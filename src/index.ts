import readline from "readline";
import { Agent } from "./agent/agent.js";
import { env } from "./config/env.js";
import { initDb } from "./memory/db.js";

// Initialize SQLite database
initDb();

const agent = new Agent();

console.log("==================================================");
console.log("🦅  ZackClaw AI Agent - Autonomous Local Assistant");
console.log("==================================================");
console.log(`🤖 Primary Provider: Groq (${env.GROQ_MODEL})`);
console.log(`✨ Fallback Provider: Gemini (${env.GEMINI_MODEL})`);
console.log(`💾 Memory Database: ${env.DB_PATH}`);
console.log("==================================================");
console.log("اكتب رسالتك واضغط Enter للتحدث مع الوكيل (أو اكتب 'exit' للخروج):");
console.log("--------------------------------------------------\n");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const context = {
  userId: 1,
  userName: "Zack",
};

function promptUser() {
  rl.question("👤 زاك > ", async (input) => {
    const trimmed = input.trim();
    if (!trimmed) {
      promptUser();
      return;
    }

    if (trimmed.toLowerCase() === "exit" || trimmed === "خروج") {
      console.log("\n👋 مع السلامة يا زاك!");
      rl.close();
      process.exit(0);
    }

    try {
      console.log("⏳ جاري التفكير...");
      const response = await agent.processMessage(context, trimmed);
      console.log(`\n🤖 ZackClaw [${response.provider} / ${response.model}]:`);
      console.log(response.text);
      if (response.toolCallsExecuted.length > 0) {
        console.log(`\n🛠️ الأدوات المنفذة: [${response.toolCallsExecuted.join(", ")}]`);
      }
      console.log("--------------------------------------------------\n");
    } catch (err: any) {
      console.error("\n❌ حدث خطأ:", err.message || err);
      console.log("--------------------------------------------------\n");
    }

    promptUser();
  });
}

promptUser();
