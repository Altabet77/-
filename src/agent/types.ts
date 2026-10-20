export interface AgentResponse {
  text: string;
  provider: "groq" | "gemini";
  model: string;
  iterations: number;
  toolCallsExecuted: string[];
}

export interface AgentContext {
  userId: number;
  userName?: string;
  chatId?: number;
}
