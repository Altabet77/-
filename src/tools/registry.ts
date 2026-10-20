import type { ToolDefinition } from "./types.js";
import { getCurrentTimeTool } from "./implementations/time.js";

export class ToolRegistry {
  private tools = new Map<string, ToolDefinition<any, any>>();

  constructor() {
    // Register default built-in tools
    this.register(getCurrentTimeTool);
  }

  /**
   * Register a new tool into the registry
   */
  register(tool: ToolDefinition<any, any>): void {
    if (this.tools.has(tool.name)) {
      console.warn(`⚠️ Tool '${tool.name}' is being overwritten.`);
    }
    this.tools.set(tool.name, tool);
  }

  /**
   * Get a tool by name
   */
  get(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }

  /**
   * Check if a tool exists
   */
  has(name: string): boolean {
    return this.tools.has(name);
  }

  /**
   * Return all tool definitions
   */
  getAll(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  /**
   * Format tool definitions for OpenAI / Groq tool calling format
   */
  toGroqTools(): Array<{
    type: "function";
    function: {
      name: string;
      description: string;
      parameters: Record<string, unknown>;
    };
  }> {
    return this.getAll().map((tool) => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters,
      },
    }));
  }

  /**
   * Format tool definitions for Gemini function calling format
   */
  toGeminiFunctionDeclarations(): Array<{
    name: string;
    description: string;
    parameters: Record<string, unknown>;
  }> {
    return this.getAll().map((tool) => ({
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters,
    }));
  }

  /**
   * Safely execute a tool by name with arguments
   */
  async execute(name: string, args: Record<string, unknown>): Promise<unknown> {
    const tool = this.tools.get(name);
    if (!tool) {
      return {
        success: false,
        error: `Tool '${name}' not found in registry.`,
      };
    }

    try {
      const result = await tool.execute(args);
      return result;
    } catch (err: any) {
      console.error(`❌ Error executing tool '${name}':`, err);
      return {
        success: false,
        error: `Tool execution failed: ${err.message || String(err)}`,
      };
    }
  }
}

// Global shared tool registry singleton
export const globalToolRegistry = new ToolRegistry();
