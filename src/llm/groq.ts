import Groq from "groq-sdk";
import type { ILLMProvider } from "./provider.js";
import type { LLMMessage, LLMResponse, LLMGenerateOptions, LLMToolCall } from "./types.js";
import type { ToolRegistry } from "../tools/registry.js";
import { env } from "../config/env.js";

export class GroqProvider implements ILLMProvider {
  readonly name = "groq" as const;
  readonly model: string;
  private client: Groq | null = null;

  constructor(model = env.GROQ_MODEL) {
    this.model = model;
    if (env.GROQ_API_KEY && env.GROQ_API_KEY !== "REPLACE_WITH_YOURS") {
      this.client = new Groq({
        apiKey: env.GROQ_API_KEY,
      });
    }
  }

  isAvailable(): boolean {
    return Boolean(this.client && env.GROQ_API_KEY && env.GROQ_API_KEY !== "REPLACE_WITH_YOURS");
  }

  async generate(
    messages: LLMMessage[],
    toolsRegistry?: ToolRegistry,
    options?: LLMGenerateOptions
  ): Promise<LLMResponse> {
    if (!this.client) {
      throw new Error("Groq client is not configured with a valid API key.");
    }

    // Format messages for Groq OpenAI-compatible format
    const formattedMessages: Groq.Chat.Completions.ChatCompletionMessageParam[] = messages.map(
      (m) => {
        if (m.role === "tool") {
          return {
            role: "tool",
            tool_call_id: m.tool_call_id || "call_unknown",
            content: m.content || "",
          };
        }

        if (m.role === "assistant" && m.tool_calls && m.tool_calls.length > 0) {
          return {
            role: "assistant",
            content: m.content || null,
            tool_calls: m.tool_calls.map((tc) => ({
              id: tc.id,
              type: "function" as const,
              function: {
                name: tc.function.name,
                arguments: tc.function.arguments,
              },
            })),
          };
        }

        if (m.role === "system") {
          return {
            role: "system",
            content: m.content || "",
          };
        }

        if (m.role === "assistant") {
          return {
            role: "assistant",
            content: m.content || "",
          };
        }

        return {
          role: "user",
          content: m.content || "",
        };
      }
    );

    const tools = toolsRegistry ? toolsRegistry.toGroqTools() : [];

    const completion = await this.client.chat.completions.create({
      model: this.model,
      messages: formattedMessages,
      tools: tools.length > 0 ? (tools as any) : undefined,
      tool_choice: tools.length > 0 ? "auto" : undefined,
      temperature: options?.temperature ?? 0.7,
      max_completion_tokens: options?.maxTokens ?? 2048,
    });

    const choice = completion.choices[0];
    if (!choice) {
      throw new Error("No response choice returned from Groq API.");
    }

    let parsedToolCalls: LLMToolCall[] | undefined;
    if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
      parsedToolCalls = choice.message.tool_calls.map((tc) => ({
        id: tc.id,
        type: "function" as const,
        function: {
          name: tc.function.name,
          arguments: tc.function.arguments,
        },
      }));
    }

    return {
      content: choice.message.content ?? null,
      tool_calls: parsedToolCalls,
      provider: "groq",
      model: this.model,
      usage: {
        promptTokens: completion.usage?.prompt_tokens,
        completionTokens: completion.usage?.completion_tokens,
        totalTokens: completion.usage?.total_tokens,
      },
    };
  }
}
