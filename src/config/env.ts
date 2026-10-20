import dotenv from "dotenv";
import { z } from "zod";

// Load .env file
dotenv.config();

const envSchema = z.object({
  TELEGRAM_BOT_TOKEN: z.string().optional().default(""),
  ALLOWED_TELEGRAM_USER_IDS: z
    .string()
    .optional()
    .default("")
    .transform((val) =>
      val
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean)
        .map((id) => Number(id))
        .filter((num) => !isNaN(num))
    ),
  GROQ_API_KEY: z.string().optional().default(""),
  GROQ_MODEL: z.string().default("llama-3.3-70b-versatile"),
  GEMINI_API_KEY: z.string().optional().default(""),
  GEMINI_MODEL: z.string().default("gemini-2.5-flash"),
  DB_PATH: z.string().default("./memory.db"),
  GOOGLE_APPLICATION_CREDENTIALS: z.string().optional(),
  MAX_AGENT_ITERATIONS: z.coerce.number().int().positive().default(5),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error("❌ Invalid environment variables configuration:");
  console.error(JSON.stringify(parsed.error.format(), null, 2));
  console.error("\n👉 Please check your .env file and ensure all required fields are set.");
}

export const env = parsed.success
  ? parsed.data
  : {
      TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN || "",
      ALLOWED_TELEGRAM_USER_IDS: (process.env.ALLOWED_TELEGRAM_USER_IDS || "")
        .split(",")
        .map((id) => Number(id.trim()))
        .filter((n) => !isNaN(n)),
      GROQ_API_KEY: process.env.GROQ_API_KEY || "",
      GROQ_MODEL: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
      GEMINI_API_KEY: process.env.GEMINI_API_KEY || "",
      GEMINI_MODEL: process.env.GEMINI_MODEL || "gemini-2.5-flash",
      DB_PATH: process.env.DB_PATH || "./memory.db",
      GOOGLE_APPLICATION_CREDENTIALS: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      MAX_AGENT_ITERATIONS: Number(process.env.MAX_AGENT_ITERATIONS) || 5,
    };

export function isUserWhitelisted(userId: number): boolean {
  if (env.ALLOWED_TELEGRAM_USER_IDS.length === 0) {
    return false;
  }
  return env.ALLOWED_TELEGRAM_USER_IDS.includes(userId);
}
