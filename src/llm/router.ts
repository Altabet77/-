import type { ILLMProvider } from "./provider.js";
import { GroqProvider } from "./groq.js";
import { GeminiProvider } from "./gemini.js";
import type { LLMMessage, LLMResponse, LLMGenerateOptions } from "./types.js";
import type { ToolRegistry } from "../tools/registry.js";

export class LLMRouter implements ILLMProvider {
  readonly name = "groq" as const;
  readonly model: string;
  private primary: GroqProvider;
  private fallback: GeminiProvider;

  constructor() {
    this.primary = new GroqProvider();
    this.fallback = new GeminiProvider();
    this.model = this.primary.model;
  }

  isAvailable(): boolean {
    return this.primary.isAvailable() || this.fallback.isAvailable();
  }

  async generate(
    messages: LLMMessage[],
    toolsRegistry?: ToolRegistry,
    options?: LLMGenerateOptions
  ): Promise<LLMResponse> {
    // 1. Try Primary LLM (Groq)
    if (this.primary.isAvailable()) {
      try {
        return await this.primary.generate(messages, toolsRegistry, options);
      } catch (err: any) {
        console.warn(
          `⚠️ Primary LLM (Groq: ${this.primary.model}) failed: ${err.message || String(err)}`
        );

        // Check if fallback is available
        if (this.fallback.isAvailable()) {
          console.log(`🔄 Switching to Fallback LLM (Gemini: ${this.fallback.model})...`);
          try {
            return await this.fallback.generate(messages, toolsRegistry, options);
          } catch (fallbackErr: any) {
            console.error(
              `❌ Fallback LLM (Gemini) also failed: ${fallbackErr.message || String(fallbackErr)}`
            );
            throw new Error(
              `Both Groq and Gemini failed.\nPrimary error: ${err.message}\nFallback error: ${fallbackErr.message}`
            );
          }
        } else {
          console.warn("⚠️ Fallback Gemini LLM is not configured in .env (GEMINI_API_KEY).");
          throw err;
        }
      }
    }

    // 2. If Groq is not configured, try Gemini directly
    if (this.fallback.isAvailable()) {
      console.log(`ℹ️ Primary LLM not configured, using Gemini directly...`);
      return await this.fallback.generate(messages, toolsRegistry, options);
    }

    throw new Error(
      "❌ No LLM providers available. Please configure GROQ_API_KEY or GEMINI_API_KEY in your .env file."
    );
  }
}
