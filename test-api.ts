import { GroqProvider } from "./src/llm/groq.js";
import { GeminiProvider } from "./src/llm/gemini.js";

async function runTest() {
  console.log("==========================================");
  console.log("🧪 Testing Groq & Gemini Connections...");
  console.log("==========================================");

  const groq = new GroqProvider();
  if (groq.isAvailable()) {
    try {
      console.log("Testing Groq (llama-3.3-70b-versatile)...");
      const res = await groq.generate([{ role: "user", content: "رد بكلمة واحدة: جاهز" }]);
      console.log("✅ Groq متصل وشغال بنجاح! الرد:", res.content);
    } catch (e: any) {
      console.error("❌ Groq Error:", e.message || e);
    }
  } else {
    console.log("⚠️ Groq غير مفعل أو المفتاح غير مضبوط");
  }

  console.log("\n------------------------------------------");
  const gemini = new GeminiProvider();
  if (gemini.isAvailable()) {
    try {
      console.log("Testing Gemini (gemini-2.5-flash)...");
      const res = await gemini.generate([{ role: "user", content: "رد بكلمة واحدة: جاهز" }]);
      console.log("✅ Gemini متصل وشغال بنجاح! الرد:", res.content);
    } catch (e: any) {
      console.error("❌ Gemini Error:", e.message || e);
    }
  } else {
    console.log("⚠️ Gemini غير مفعل أو المفتاح غير مضبوط");
  }
  console.log("==========================================");
  process.exit(0);
}

runTest();
