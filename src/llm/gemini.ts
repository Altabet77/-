import { GoogleGenerativeAI, type FunctionDeclaration, type Content } from "@google/generative-ai";
import type { ILLMProvider } from "./provider.js";
import type { LLMMessage, LLMResponse, LLMGenerateOptions, LLMToolCall } from "./types.js";
import type { ToolRegistry } from "../tools/registry.js";
import { env } from "../config/env.js";

export class GeminiProvider implements ILLMProvider {
  readonly name = "gemini" as const;
  readonly model: string;
  private client: GoogleGenerativeAI | null = null;

  constructor(model = env.GEMINI_MODEL) {
    this.model = model;
    if (env.GEMINI_API_KEY && env.GEMINI_API_KEY !== "REPLACE_WITH_YOURS") {
      this.client = new GoogleGenerativeAI(env.GEMINI_API_KEY);
    }
  }

  isAvailable(): boolean {
    return Boolean(this.client && env.GEMINI_API_KEY && env.GEMINI_API_KEY !== "REPLACE_WITH_YOURS");
  }

  async generate(
    messages: LLMMessage[],
    toolsRegistry?: ToolRegistry,
    options?: LLMGenerateOptions
  ): Promise<LLMResponse> {
    if (!this.client) {
      throw new Error("Gemini client is not configured with a valid API key.");
    }

    // Extract system message if present
    const systemMsg = messages.find((m) => m.role === "system");
    const nonSystemMessages = messages.filter((m) => m.role !== "system");

    // Format function declarations for Gemini
    let functionDeclarations: FunctionDeclaration[] | undefined;
    if (toolsRegistry && toolsRegistry.getAll().length > 0) {
      functionDeclarations = toolsRegistry.getAll().map((tool) => ({
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters as any,
      }));
    }

    const genModel = this.client.getGenerativeModel({
      model: this.model,
      systemInstruction: systemMsg?.content,
      tools: functionDeclarations ? [{ functionDeclarations }] : undefined,
      generationConfig: {
        temperature: options?.temperature ?? 0.7,
        maxOutputTokens: options?.maxTokens ?? 2048,
      },
    });

    // Format contents history
    const contents: Content[] = [];

    for (const m of nonSystemMessages) {
      if (m.role === "user") {
        contents.push({
          role: "user",
          parts: [{ text: m.content || "" }],
        });
      } else if (m.role === "assistant") {
        if (m.tool_calls && m.tool_calls.length > 0) {
          const parts: any[] = [];
          if (m.content) {
            parts.push({ text: m.content });
          }
          for (const tc of m.tool_calls) {
            let parsedArgs = {};
            try {
              parsedArgs = JSON.parse(tc.function.arguments);
            } catch {
              parsedArgs = {};
            }
            parts.push({
              functionCall: {
                name: tc.function.name,
                args: parsedArgs,
              },
            });
          }
          contents.push({
            role: "model",
            parts,
          });
        } else {
          contents.push({
            role: "model",
            parts: [{ text: m.content || "" }],
          });
        }
      } else if (m.role === "tool") {
        let parsedResult: any = {};
        try {
          parsedResult = JSON.parse(m.content);
        } catch {
          parsedResult = { result: m.content };
        }

        contents.push({
          role: "user",
          parts: [
            {
              functionResponse: {
                name: m.name || "unknown_tool",
                response: parsedResult,
              },
            },
          ],
        });
      }
    }

    const result = await genModel.generateContent({
      contents,
    });

    const response = result.response;
    const candidates = response.candidates;
    const firstCandidate = candidates?.[0];

    if (!firstCandidate) {
      throw new Error("No candidate returned from Gemini API.");
    }

    let parsedToolCalls: LLMToolCall[] | undefined;
    let textContent: string | null = null;

    const parts = firstCandidate.content.parts;
    for (const part of parts) {
      if (part.text) {
        textContent = (textContent ? textContent + "\n" : "") + part.text;
      }
      if (part.functionCall) {
        if (!parsedToolCalls) parsedToolCalls = [];
        parsedToolCalls.push({
          id: `gemini_call_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
          type: "function",
          function: {
            name: part.functionCall.name,
            arguments: JSON.stringify(part.functionCall.args || {}),
          },
        });
      }
    }

    return {
      content: textContent,
      tool_calls: parsedToolCalls,
      provider: "gemini",
      model: this.model,
      usage: {
        promptTokens: response.usageMetadata?.promptTokenCount,
        completionTokens: response.usageMetadata?.candidatesTokenCount,
        totalTokens: response.usageMetadata?.totalTokenCount,
      },
    };
  }
}
