import type { ILLMProvider } from "../llm/provider.js";
import { LLMRouter } from "../llm/router.js";
import { ToolRegistry, globalToolRegistry } from "../tools/registry.js";
import { ConversationRepository } from "../memory/conversation.js";
import { buildSystemPrompt } from "./prompt.js";
import type { AgentContext, AgentResponse } from "./types.js";
import type { LLMMessage } from "../llm/types.js";
import { env } from "../config/env.js";

export class Agent {
  private router: ILLMProvider;
  private toolRegistry: ToolRegistry;
  private maxIterations: number;

  constructor(
    router: ILLMProvider = new LLMRouter(),
    toolRegistry: ToolRegistry = globalToolRegistry,
    maxIterations = env.MAX_AGENT_ITERATIONS
  ) {
    this.router = router;
    this.toolRegistry = toolRegistry;
    this.maxIterations = maxIterations;
  }

  /**
   * Process an incoming user message through the agent loop
   */
  async processMessage(context: AgentContext, userText: string): Promise<AgentResponse> {
    const { userId, userName } = context;

    // 1. Save incoming user message to SQLite persistent conversation store
    const userMsg: LLMMessage = { role: "user", content: userText };
    ConversationRepository.saveMessage(userId, userMsg);

    // 2. Fetch recent conversation history
    const history = ConversationRepository.getRecentMessages(userId, 20);

    // 3. Build system instruction prompt with persona & memories
    const systemPrompt = buildSystemPrompt(userId, userName);
    const systemMsg: LLMMessage = { role: "system", content: systemPrompt };

    // Construct working memory for this reasoning session
    const workingMessages: LLMMessage[] = [systemMsg, ...history];

    let iteration = 0;
    const executedTools: string[] = [];
    let lastProvider: "groq" | "gemini" = "groq";
    let lastModel = env.GROQ_MODEL;

    while (iteration < this.maxIterations) {
      iteration++;

      console.log(`🤖 [Agent Loop] User: ${userId} | Iteration: ${iteration}/${this.maxIterations}`);

      // Generate response from LLM router
      const response = await this.router.generate(workingMessages, this.toolRegistry);
      lastProvider = response.provider;
      lastModel = response.model;

      // Check if LLM requested tool execution
      if (response.tool_calls && response.tool_calls.length > 0) {
        console.log(
          `🛠️ [Tool Request] Detected ${response.tool_calls.length} tool call(s): ${response.tool_calls.map((t) => t.function.name).join(", ")}`
        );

        // Record assistant turn with tool calls
        const assistantTurn: LLMMessage = {
          role: "assistant",
          content: response.content || "",
          tool_calls: response.tool_calls,
        };
        workingMessages.push(assistantTurn);
        ConversationRepository.saveMessage(userId, assistantTurn);

        // Execute each requested tool
        for (const toolCall of response.tool_calls) {
          const toolName = toolCall.function.name;
          executedTools.push(toolName);

          let parsedArgs = {};
          try {
            parsedArgs = JSON.parse(toolCall.function.arguments || "{}");
          } catch (e) {
            console.error(`⚠️ Failed to parse arguments for tool ${toolName}:`, e);
          }

          console.log(`⚡ Executing tool '${toolName}' with args:`, parsedArgs);
          const toolResult = await this.toolRegistry.execute(toolName, parsedArgs);

          const toolResponseTurn: LLMMessage = {
            role: "tool",
            name: toolName,
            tool_call_id: toolCall.id,
            content: JSON.stringify(toolResult),
          };

          workingMessages.push(toolResponseTurn);
          ConversationRepository.saveMessage(userId, toolResponseTurn);
        }

        // Loop back to give LLM the tool results
        continue;
      }

      // If no tool calls, we have the final assistant response
      const finalText = response.content || "I have processed your request.";

      const assistantFinalTurn: LLMMessage = {
        role: "assistant",
        content: finalText,
      };
      ConversationRepository.saveMessage(userId, assistantFinalTurn);

      return {
        text: finalText,
        provider: lastProvider,
        model: lastModel,
        iterations: iteration,
        toolCallsExecuted: executedTools,
      };
    }

    // Safety guard if max iterations reached
    const fallbackText =
      "⚠️ Reached the maximum execution loop limit without concluding. Please try phrasing your request with more specificity.";

    return {
      text: fallbackText,
      provider: lastProvider,
      model: lastModel,
      iterations: iteration,
      toolCallsExecuted: executedTools,
    };
  }
}
