export interface JSONSchemaProperty {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  description?: string;
  enum?: string[];
  items?: JSONSchemaProperty;
  properties?: Record<string, JSONSchemaProperty>;
  required?: string[];
  [key: string]: unknown;
}

export interface ToolParametersSchema {
  type: "object";
  properties: Record<string, JSONSchemaProperty>;
  required?: string[];
  [key: string]: unknown;
}

export interface ToolDefinition<TArgs = Record<string, unknown>, TResult = unknown> {
  name: string;
  description: string;
  parameters: ToolParametersSchema;
  execute: (args: TArgs) => Promise<TResult> | TResult;
}
