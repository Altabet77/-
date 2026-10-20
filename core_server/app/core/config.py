import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "samir_secret_jwt_key_2026"
    ALLOWED_ORIGINS: str = "*"

    # AI Provider
    DEFAULT_AI_PROVIDER: str = "gemini"
    GROQ_API_KEY: str = ""
    GROQ_CHAT_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_STT_MODEL: str = "whisper-large-v3"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = ""

    # Qwen (Alibaba Cloud DashScope / Qwen)
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen2.5-72b-instruct"

    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # DuckDuckGo AI (duck.ai) — مجاني بدون مفتاح API
    DUCKAI_MODEL: str = "gpt-4o-mini"
    DUCKAI_ENABLED: bool = True

    # ElevenLabs Voice Settings
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    DEFAULT_TTS_VOICE: str = "pNInz6obpgDQGcFmaJgB"  # Adam (ElevenLabs)
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"
    TTS_VOLUME: str = "+0%"

    # Storage
    DB_PATH: str = str(BASE_DIR / "data" / "samir.db")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure data directory exists
os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
