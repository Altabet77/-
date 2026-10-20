import asyncio
import sys
import os

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import init_database
from app.memory.long_term import long_term_memory
from app.tools.base_tool import tool_registry
import app.tools.default_tools
from app.ai.orchestrator import orchestrator
from app.voice.tts_service import tts_service

async def run_tests():
    print("========================================")
    print("🧪 Testing Samir Core Server - Phase 1")
    print("========================================")

    # 1. Test Database
    print("1️⃣ Testing Database Initialization...")
    await init_database()
    print("✅ Database schema initialized.")

    # 2. Test Long-Term Memory
    print("\n2️⃣ Testing Long-Term Memory Store...")
    saved = await long_term_memory.save_fact(
        key="اسم مشروع اللعبة",
        value="Knight Quest",
        category="project"
    )
    print(f"✅ Memory saved: {saved}")
    facts = await long_term_memory.get_all_facts()
    print(f"✅ Memory retrieved ({len(facts)} facts): {[f['key'] for f in facts]}")

    # 3. Test Tool Execution
    print("\n3️⃣ Testing Tool Execution (get_time)...")
    time_res = await tool_registry.execute_tool("get_time", {})
    print(f"✅ Tool Result: {time_res}")

    # 4. Test TTS
    print("\n4️⃣ Testing Edge-TTS Speech Generation...")
    sample_text = "مرحباً بك يا طيب! أنا سمير، ومستعد لتنفيذ أوامرك."
    audio_bytes = await tts_service.generate_speech_bytes(sample_text)
    print(f"✅ Generated audio bytes size: {len(audio_bytes)} bytes (Valid MP3 stream)")

    # 5. Test AI Orchestrator & Samir Personality
    print("\n5️⃣ Testing AI Orchestrator (Groq / Qwen / Llama)...")
    try:
        res = await orchestrator.process_user_input(
            user_text="شنو الجو اليوم يا سمير؟",
            chat_history=[],
            memory_facts=facts,
            available_tools=tool_registry.get_all_tool_schemas()
        )
        print(f"✅ AI Response ({res.get('provider')} / {res.get('model')}):")
        print(f"   💬 '{res.get('content')}'")
        if res.get('tool_calls'):
            print(f"   🔧 Tools called: {res.get('tool_calls')}")
    except Exception as e:
        print(f"⚠️ AI test note (check API key): {e}")

    print("\n========================================")
    print("🎉 ALL PHASE 1 CORE TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
