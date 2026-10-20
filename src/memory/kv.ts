import { getDatabase } from "./db.js";

export class KeyValueMemory {
  /**
   * Set a key-value pair in persistent memory
   */
  static set(key: string, value: unknown): void {
    const db = getDatabase();
    const strValue = typeof value === "string" ? value : JSON.stringify(value);
    const stmt = db.prepare(`
      INSERT INTO key_value_store (key, value, updated_at)
      VALUES (?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        updated_at = CURRENT_TIMESTAMP
    `);
    stmt.run(key, strValue);
  }

  /**
   * Get a value from persistent memory
   */
  static get<T = unknown>(key: string): T | null {
    const db = getDatabase();
    const stmt = db.prepare(`SELECT value FROM key_value_store WHERE key = ?`);
    const row = stmt.get(key) as { value: string } | undefined;
    if (!row) return null;

    try {
      return JSON.parse(row.value) as T;
    } catch {
      return row.value as unknown as T;
    }
  }

  /**
   * Delete a key from memory
   */
  static delete(key: string): boolean {
    const db = getDatabase();
    const stmt = db.prepare(`DELETE FROM key_value_store WHERE key = ?`);
    const result = stmt.run(key);
    return result.changes > 0;
  }

  /**
   * List all stored memories
   */
  static getAll(): Record<string, unknown> {
    const db = getDatabase();
    const stmt = db.prepare(`SELECT key, value FROM key_value_store`);
    const rows = stmt.all() as { key: string; value: string }[];
    const result: Record<string, unknown> = {};

    for (const row of rows) {
      try {
        result[row.key] = JSON.parse(row.value);
      } catch {
        result[row.key] = row.value;
      }
    }

    return result;
  }
}
