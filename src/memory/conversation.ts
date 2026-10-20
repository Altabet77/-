import { getDatabase } from "./db.js";
import type { LLMMessage } from "../llm/types.js";

export interface StoredMessage {
  id: number;
  user_id: number;
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls: string | null;
  tool_call_id: string | null;
  name: string | null;
  created_at: string;
}

export class ConversationRepository {
  /**
   * Save a message into persistent memory
   */
  static saveMessage(userId: number, msg: LLMMessage): void {
    const db = getDatabase();
    const stmt = db.prepare(`
      INSERT INTO messages (user_id, role, content, tool_calls, tool_call_id, name)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const toolCallsJson = msg.tool_calls ? JSON.stringify(msg.tool_calls) : null;
    stmt.run(
      userId,
      msg.role,
      msg.content ?? null,
      toolCallsJson,
      msg.tool_call_id ?? null,
      msg.name ?? null
    );
  }

  /**
   * Fetch the most recent N messages for this user formatted as LLMMessages
   */
  static getRecentMessages(userId: number, limit = 20): LLMMessage[] {
    const db = getDatabase();
    const stmt = db.prepare(`
      SELECT * FROM (
        SELECT id, user_id, role, content, tool_calls, tool_call_id, name, created_at
        FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
      ) sub
      ORDER BY id ASC
    `);

    const rows = stmt.all(userId, limit) as StoredMessage[];

    return rows.map((row) => {
      const msg: LLMMessage = {
        role: row.role,
        content: row.content ?? "",
      };

      if (row.tool_calls) {
        try {
          msg.tool_calls = JSON.parse(row.tool_calls);
        } catch {
          // Ignore parse errors
        }
      }

      if (row.tool_call_id) {
        msg.tool_call_id = row.tool_call_id;
      }

      if (row.name) {
        msg.name = row.name;
      }

      return msg;
    });
  }

  /**
   * Clear all conversation history for this user
   */
  static clearHistory(userId: number): number {
    const db = getDatabase();
    const stmt = db.prepare(`DELETE FROM messages WHERE user_id = ?`);
    const result = stmt.run(userId);
    return result.changes;
  }

  /**
   * Get total message count stored for user
   */
  static getMessageCount(userId: number): number {
    const db = getDatabase();
    const stmt = db.prepare(`SELECT COUNT(*) as count FROM messages WHERE user_id = ?`);
    const row = stmt.get(userId) as { count: number };
    return row?.count ?? 0;
  }
}
