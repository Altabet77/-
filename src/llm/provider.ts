import type { LLMMessage, LLMResponse, LLMGenerateOptions } from "./types.js";
import type { ToolRegistry } from "../tools/registry.js";

export interface ILLMProvider {
  readonly name: "groq" | "gemini";
  readonly model: string;
  isAvailable(): boolean;
  generate(
    messages: LLMMessage[],
    toolsRegistry?: ToolRegistry,
    options?: LLMGenerateOptions
  ): Promise<LLMResponse>;
}
