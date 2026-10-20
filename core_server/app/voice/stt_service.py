import io
import re
import base64
import logging
from typing import Optional
import httpx
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger("samir.voice.stt")

# تلقين مسبق لمساعد Whisper للتعرف على اللهجة الليبية والعربية والأسماء التقنية
LIBYAN_ARABIC_WHISPER_PROMPT = (
    "محادثة باللغة العربية واللهجة الليبية مع المساعد الذكي سمير. "
    "كلمات شائعة: سمير، شنو الجو، تمام يا طيب، شن صار، باهي، ديرلي، شوفلي، "
    "افتح Discord, Brave, YouTube, OBS, DaVinci Resolve, Knight Quest, Claude, VS Code."
)

COMMON_HALLUCINATIONS = [
    "اشتركوا في القناة", "اشترك في القناة", "شكرا للمشاهدة", "شكراً للمشاهدة",
    "مرحبا بكم في القناة", "لاتنسوا الاشتراك", "لا تنسوا الاشتراك",
    "subtitles by", "subscribe to", "thank you for watching", "watching!",
    "ترجمة نانسي قنقر", "ترجمة", "نانسي قنقر", "تُرجمت بواسطة",
    "[صمت]", "[موسيقى]", "[ضحك]", "[تصفيق]"
]


class STTService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: str = "ar"
    ) -> str:
        """
        تحويل الصوت إلى نص بدقة وسرعة فائقة مع نظام احتياطي متعدد الطبقات:
        1. Groq Whisper Large v3 Turbo (فائق السرعة ~200ms)
        2. Groq Whisper Large v3
        3. Gemini 3.5 Flash Lite (احتياطي سحابي قوي لا يضرب rate limit نهائياً)
        """
        if not audio_bytes or len(audio_bytes) < 400:
            logger.debug("Audio bytes too small (<400 bytes), skipping STT.")
            return ""

        # المحاولة 1: Groq Whisper
        text = await self._transcribe_groq(audio_bytes, filename, language)

        # المحاولة 2: إذا فشل Groq، نلجأ إلى Gemini كـ Fallback فوري
        if not text and settings.GEMINI_API_KEY:
            logger.info("Groq STT returned empty or failed. Attempting Gemini STT fallback...")
            text = await self._transcribe_gemini(audio_bytes, filename)

        # فلترة الهلوسات
        cleaned = self._clean_transcription(text)
        if cleaned:
            logger.info(f"Final STT Transcription result: '{cleaned}'")
        return cleaned

    async def _transcribe_groq(self, audio_bytes: bytes, filename: str, language: str) -> str:
        if not self.client:
            return ""

        models_to_try = [
            "whisper-large-v3-turbo",
            settings.GROQ_STT_MODEL or "whisper-large-v3"
        ]
        # إزالة التكرار مع الحفاظ على الترتيب
        seen = set()
        models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        for model in models:
            try:
                audio_file = (filename, io.BytesIO(audio_bytes))
                transcription = await self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=model,
                    prompt=LIBYAN_ARABIC_WHISPER_PROMPT,
                    language=language,
                    temperature=0.0
                )
                text = (transcription.text or "").strip()
                if text:
                    return text
            except Exception as e:
                logger.warning(f"Groq STT model '{model}' error: {e}")

        return ""

    async def _transcribe_gemini(self, audio_bytes: bytes, filename: str) -> str:
        try:
            mime_type = "audio/webm"
            if filename.endswith(".wav"):
                mime_type = "audio/wav"
            elif filename.endswith(".mp4") or filename.endswith(".m4a"):
                mime_type = "audio/mp4"
            elif filename.endswith(".mp3"):
                mime_type = "audio/mp3"
            elif filename.endswith(".ogg"):
                mime_type = "audio/ogg"

            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # استخدام gemini-2.0-flash لأنه يدعم الصوت بشكل مثالي
            gemini_audio_model = "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_audio_model}:generateContent?key={settings.GEMINI_API_KEY}"

            prompt_text = (
                "قم بتحويل هذا التسجيل الصوتي بدقة إلى نص مكتوب باللغة العربية (أو اللهجة الليبية/العامية) "
                "كما نطقها المتحدث تماماً بدون أي شروحات أو مقدمات أو علامات إضافية. "
                "إذا كان التسجيل عبارة عن صمت تام أو تشويش بدون كلام مفيد، أرجع فقط: [صمت]"
            )

            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": audio_b64}},
                        {"text": prompt_text}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 256
                }
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        txt = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                        return txt
                else:
                    logger.warning(f"Gemini STT fallback failed: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Error in Gemini STT fallback: {e}")

        return ""


    def _clean_transcription(self, text: str) -> str:
        if not text:
            return ""

        text_clean = text.strip()
        lower_text = text_clean.lower()

        # فحص الهلوسات الشائعة
        for h in COMMON_HALLUCINATIONS:
            if h.lower() in lower_text:
                logger.info(f"Ignoring hallucination match '{h}': '{text_clean}'")
                return ""

        # فحص إذا كان صمتاً أو بدون أحرف مفيدة
        stripped_symbols = re.sub(r'[\s\.\,\!\؟\-\_\[\]\(\)]', '', text_clean)
        if len(stripped_symbols) < 2:
            return ""

        return text_clean


stt_service = STTService()
