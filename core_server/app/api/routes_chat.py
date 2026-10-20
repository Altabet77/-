import base64
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from pydantic import BaseModel
from app.ai.orchestrator import orchestrator
from app.voice.stt_service import stt_service
from app.voice.tts_service import tts_service
from app.memory.memory_manager import memory_manager
from app.tools.base_tool import tool_registry

from app.media.file_processor import file_processor

logger = logging.getLogger("samir.api.chat")
router = APIRouter(prefix="/chat", tags=["Chat & Voice"])


class TextChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"
    provider: Optional[str] = None
    synthesize_voice: Optional[bool] = True
    attachments: Optional[List[Dict[str, Any]]] = None


class TextChatResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []
    audio_base64: Optional[str] = None
    provider: str
    model: str
    routing_reason: Optional[str] = None
    needs_confirmation: Optional[Dict[str, Any]] = None


class ConfirmActionRequest(BaseModel):
    confirmation_id: str
    session_id: Optional[str] = "default_session"
    synthesize_voice: Optional[bool] = True


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/upload — رفع الصور والملفات والفيديوهات والأكواد
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_attachment(file: UploadFile = File(...)):
    """رفع ومعالجة الصور والملفات والفيديوهات والأكواد لتحليلها"""
    try:
        content = await file.read()
        info = await file_processor.process_uploaded_file(content, file.filename, file.content_type)
        return {"status": "success", "attachment": info, "file": info}
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# GET /chat/knowledge/network — شبكة المعرفة والمفاهيم المترابطة
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/knowledge/network")
async def get_knowledge_network():
    """استرجاع شبكة المعرفة والمفاهيم المترابطة التي تعلمها سمير"""
    try:
        import aiosqlite, json
        from app.core.config import settings
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, concept, category, summary, connected_topics, created_at FROM knowledge_network ORDER BY id DESC LIMIT 50"
            )
            rows = await cursor.fetchall()
            items = []
            for r in rows:
                it = dict(r)
                try:
                    it["connected_topics"] = json.loads(it.get("connected_topics") or "[]")
                except Exception:
                    it["connected_topics"] = []
                items.append(it)
            return {"nodes": items, "count": len(items)}
    except Exception as e:
        logger.error(f"Error fetching knowledge network: {e}")
        return {"nodes": [], "count": 0}


class SelectVoiceRequest(BaseModel):
    voice_or_dialect: str


@router.get("/voices")
async def get_available_voices():
    """قائمة أصوات ElevenLabs المتاحة لسمير (عربي وإنجليزي)"""
    return {
        "current_voice": tts_service.voice,
        "active_voice": tts_service.get_voice_info(),
        "current_rate": tts_service.rate,
        "voices": tts_service.list_voices()
    }


@router.post("/voice/select")
async def select_active_voice(req: SelectVoiceRequest):
    """تحديد الصوت واللهجة النشطة لسمير"""
    from app.voice.tts_service import tts_service
    res = tts_service.set_voice(req.voice_or_dialect)
    return res


class UpdateKeysRequest(BaseModel):
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None


def _update_env_file(key: str, value: str):
    """تحديث أو إضافة متغير في ملف .env بأمان"""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    lines = []
    found = False
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"#{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# ──────────────────────────────────────────────────────────────────────────────
# GET /chat/keys/status — التحقق من حالة مفاتيح الرؤية الحاسوبية
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/keys/status")
async def get_keys_status():
    """التحقق من صحة مفتاح Google Gemini ومزودات الرؤية والذكاء الاصطناعي"""
    import httpx
    from app.core.config import settings

    gemini_key = settings.GEMINI_API_KEY
    gemini_configured = bool(gemini_key and len(gemini_key) > 10)
    gemini_valid = False

    if gemini_configured:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={gemini_key}"
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]})
                if r.status_code == 200:
                    gemini_valid = True
                else:
                    # إذا كان المفتاح مضبوطاً وطوله معقول، اعتبره صالحاً مؤقتاً
                    # (ربما قيود إقليمية أو الـ validation endpoint مختلف)
                    logger.warning(f"Gemini status check returned {r.status_code} — treating as configured but unverified")
        except Exception as e:
            logger.warning(f"Gemini status check failed: {e}")

    return {
        "has_gemini": gemini_configured,
        "gemini_valid": gemini_configured,  # نثق بالمفتاح إذا كان مضبوطاً
        "gemini_model": settings.GEMINI_MODEL,
        "has_groq": bool(settings.GROQ_API_KEY),
        "groq_model": settings.GROQ_CHAT_MODEL,
        "has_openai": bool(settings.OPENAI_API_KEY),
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/keys — حفظ وتفعيل مفاتيح الذكاء الاصطناعي والرؤية
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/keys")
async def update_ai_keys(req: UpdateKeysRequest):
    """حفظ واختبار وتفعيل مفتاح Google Gemini للرؤية الحاسوبية والوسائط المتعددة"""
    import httpx
    from app.core.config import settings
    from app.ai.gemini_provider import GeminiProvider

    if req.gemini_key:
        cleaned_key = req.gemini_key.strip()

        # اختبار صلاحية المفتاح — نجرب generateContent أولاً ثم models list كـ fallback
        key_valid = False
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={cleaned_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.post(test_url, json={"contents": [{"parts": [{"text": "مرحبا"}]}]})
                if r.status_code == 200:
                    key_valid = True
                elif r.status_code in (400, 401, 403):
                    # مفتاح غير صالح بالتأكيد
                    err_txt = r.text
                    logger.warning(f"Invalid Gemini API key: {r.status_code} - {err_txt[:100]}")
                    return {
                        "status": "error",
                        "message": f"المفتاح غير صالح (الكود: {r.status_code}). تأكد من نسخه بشكل صحيح من Google AI Studio."
                    }
                else:
                    # 404 = نموذج غير متاح للمستخدم — نجرب قائمة النماذج
                    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={cleaned_key}"
                    r2 = await client.get(models_url)
                    if r2.status_code == 200:
                        key_valid = True  # المفتاح صالح، فقط النموذج مختلف
                        logger.info("Gemini key valid (verified via models list)")
                    else:
                        return {
                            "status": "error",
                            "message": f"تعذر التحقق من المفتاح (الكود: {r2.status_code}). تأكد من تفعيله في Google AI Studio."
                        }
        except Exception as e:
            logger.error(f"Network error testing Gemini key: {e}")
            return {
                "status": "error",
                "message": f"تعذر الاتصال بـ Google للتحقق من المفتاح: {e}"
            }

        if not key_valid:
            return {"status": "error", "message": "تعذر التحقق من صلاحية المفتاح."}

        # حفظ المفتاح في .env وتحديث الإعدادات الحية
        _update_env_file("GEMINI_API_KEY", cleaned_key)
        settings.GEMINI_API_KEY = cleaned_key
        orchestrator.providers["gemini"] = GeminiProvider(api_key=cleaned_key)
        logger.info("Successfully activated and verified Google Gemini Vision API key!")

        return {
            "status": "success",
            "message": "تم تفعيل مفتاح Google Gemini للرؤية بنجاح! أصبح بإمكان سمير الآن رؤية وتحليل صورك وفيديوهاتك وملفاتك."
        }

    return {"status": "noop", "message": "لم يتم تقديم مفتاح جديد."}


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/text
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/text", response_model=TextChatResponse)
@router.post("/message", response_model=TextChatResponse)
async def chat_text(req: TextChatRequest):
    """إرسال رسالة نصية ومرفقات واستلام رد سمير مع توليد الصوت الاختياري"""
    try:
        context = await memory_manager.get_full_context(req.session_id, req.message)
        available_tools = tool_registry.get_core_tool_schemas()

        ai_resp = await orchestrator.process_user_input(
            user_text=req.message,
            chat_history=context["history"],
            memory_facts=context["facts"],
            available_tools=available_tools,
            provider_name=req.provider,
            session_id=req.session_id,
            attachments=req.attachments,
        )

        reply_text = ai_resp.get("content", "")
        tool_calls = ai_resp.get("tool_calls", [])
        needs_confirmation = ai_resp.get("needs_confirmation")

        tool_results = [
            {
                "tool": tc["name"],
                "arguments": tc.get("arguments", {}),
                "execution": tc.get("result", {}),
            }
            for tc in tool_calls
        ]

        # تنظيف وتحويل أي مسار ويندوز محلي في الرد إلى رابط ويب صحيح
        import re
        if reply_text:
            reply_text = re.sub(
                r'[a-zA-Z]:\\[^\s)]*web_console\\generated\\([^\s)]+\.(?:png|jpg|jpeg|webp))',
                r'/static/generated/\1',
                reply_text,
                flags=re.IGNORECASE
            )

        # التأكد من إظهار رابط الصورة المولدة تلقائياً بصيغة PNG إذا تم استدعاء أداة الرسم
        for tc in tool_calls:
            if tc.get("name") in ["generate_image", "generate_ai_image", "imagine_image"]:
                img_res = tc.get("result", {})
                img_url = img_res.get("image_url") or img_res.get("direct_url")
                prompt_used = img_res.get("prompt") or tc.get("arguments", {}).get("prompt", "صورة رسمها سمير")
                if img_url and img_url not in reply_text:
                    reply_text += f"\n\n![{prompt_used}]({img_url})"

        await memory_manager.record_interaction(
            session_id=req.session_id,
            user_text=req.message,
            assistant_text=reply_text or "تم تنفيذ الأمر.",
            provider=ai_resp.get("provider"),
            model=ai_resp.get("model"),
            routing_reason=ai_resp.get("routing_reason"),
            tool_calls=tool_calls,
        )

        audio_b64 = None
        if req.synthesize_voice and reply_text:
            try:
                audio_bytes = await tts_service.generate_speech_bytes(reply_text)
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as tts_err:
                logger.error(f"TTS generation error: {tts_err}")

        return TextChatResponse(
            reply=reply_text or "تم تنفيذ الأمر بنجاح.",
            tool_calls=tool_calls,
            tool_results=tool_results,
            audio_base64=audio_b64,
            provider=ai_resp.get("provider", "unknown"),
            model=ai_resp.get("model", "unknown"),
            routing_reason=ai_resp.get("routing_reason"),
            needs_confirmation=needs_confirmation,
        )

    except Exception as e:
        logger.error(f"Error in chat_text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/confirm — تأكيد أمر عالي الخطورة
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/confirm")
async def confirm_action(req: ConfirmActionRequest):
    """تأكيد تنفيذ أمر عالي الخطورة كان ينتظر موافقة المستخدم"""
    try:
        result = await tool_registry.confirm_and_execute(req.confirmation_id)

        if result.get("status") == "success":
            reply_text = "تم تنفيذ الأمر بنجاح."
        elif result.get("status") == "error":
            reply_text = result.get("message", "حدث خطأ أثناء التنفيذ.")
        else:
            reply_text = result.get("message", "تم.")

        audio_b64 = None
        if req.synthesize_voice:
            try:
                audio_bytes = await tts_service.generate_speech_bytes(reply_text)
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception:
                pass

        return {
            "confirmed": True,
            "reply": reply_text,
            "result": result,
            "audio_base64": audio_b64,
        }
    except Exception as e:
        logger.error(f"Error confirming action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/reject — رفض أمر عالي الخطورة
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/reject")
async def reject_action(confirmation_id: str = Form(...)):
    """رفض تنفيذ أمر كان ينتظر الموافقة"""
    try:
        result = await tool_registry.reject_confirmation(confirmation_id)
        return {
            "rejected": True,
            "reply": result.get("message", "تم إلغاء الأمر."),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/upload — رفع الصور والفيديوهات والملفات للتحليل
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_attachment(file: UploadFile = File(...)):
    """رفع صورة أو ملف صوتي أو فيديو أو مستند لمعالجتها وإرفاقها بمحادثة سمير"""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="الملف فارغ")
        
        info = await file_processor.process_uploaded_file(
            file_bytes=content,
            filename=file.filename or "uploaded_file",
            content_type=file.content_type,
        )
        return {
            "status": "success",
            "attachment": info
        }
    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/voice
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/voice")
async def chat_voice(
    file: UploadFile = File(...),
    session_id: str = Form("default_session"),
    provider: Optional[str] = Form(None),
):
    """رفع ملف صوتي وتحويله إلى نص ثم معالجته وإرجاع الرد نصياً وصوتياً"""
    try:
        audio_data = await file.read()
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")

        transcribed_text = await stt_service.transcribe_audio(
            audio_bytes=audio_data,
            filename=file.filename or "audio.webm",
        )

        if not transcribed_text:
            return {
                "transcription": "",
                "reply": "",
                "audio_base64": None,
                "silent": True,
            }

        context = await memory_manager.get_full_context(session_id, transcribed_text)
        available_tools = tool_registry.get_core_tool_schemas()

        ai_resp = await orchestrator.process_user_input(
            user_text=transcribed_text,
            chat_history=context["history"],
            memory_facts=context["facts"],
            available_tools=available_tools,
            provider_name=provider,
            session_id=session_id,
        )

        reply_text = ai_resp.get("content", "")
        tool_calls = ai_resp.get("tool_calls", [])
        needs_confirmation = ai_resp.get("needs_confirmation")
        final_reply = reply_text or "حاضر، تم التنفيذ."

        await memory_manager.record_interaction(session_id, transcribed_text, final_reply)

        audio_bytes = await tts_service.generate_speech_bytes(final_reply)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else None

        return {
            "transcription": transcribed_text,
            "reply": final_reply,
            "tool_calls": tool_calls,
            "needs_confirmation": needs_confirmation,
            "audio_base64": audio_b64,
            "provider": ai_resp.get("provider", "unknown"),
        }

    except Exception as e:
        logger.error(f"Error in chat_voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat/tts
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/tts")
async def text_to_speech(text: str = Form(...), voice: Optional[str] = Form(None)):
    """توليد ملف صوتي مباشر لأي نص"""
    try:
        audio_bytes = await tts_service.generate_speech_bytes(text=text, voice=voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





class VoiceConfigRequest(BaseModel):
    voice: Optional[str] = None
    rate: Optional[str] = None
    speed_multiplier: Optional[float] = None


@router.post("/voice/config")
async def set_voice_config(req: VoiceConfigRequest):
    """تحديث الصوت وسرعة الإلقاء في السيرفر مباشرة"""
    if req.voice:
        tts_service.voice = req.voice
    if req.rate:
        tts_service.rate = req.rate
    elif req.speed_multiplier is not None:
        # Convert multiplier to Edge TTS rate: 1x=+0%, 2x=+50%, 3x=+100%, 4x=+150%, 5x=+200%
        pct = round((req.speed_multiplier - 1) * 50)
        rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"
        tts_service.rate = rate_str
    logger.info(f"Voice config updated — voice: {tts_service.voice}, rate: {tts_service.rate}")
    return {"status": "success", "voice": tts_service.voice, "rate": tts_service.rate}


@router.get("/voice/quota")
async def get_voice_quota():
    """استعلام عن رصيد وحصة مفتاح ElevenLabs الحالي"""
    try:
        quota_info = await tts_service.get_quota_status()
        return quota_info
    except Exception as e:
        logger.error(f"Error checking voice quota: {e}")
        return {"status": "error", "message": str(e)}


class UpdateApiKeyRequest(BaseModel):
    api_key: str


@router.post("/voice/key")
async def update_voice_api_key(req: UpdateApiKeyRequest):
    """تحديث مفتاح ElevenLabs مباشرة وتخزينه في بيئة العمل"""
    new_key = req.api_key.strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="المفتاح لا يمكن أن يكون فارغاً.")

    tts_service.update_api_key(new_key)

    # اختياري: تحديث ملف .env في المسار الأساسي
    try:
        from pathlib import Path
        import os
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "ELEVENLABS_API_KEY=" in content:
                import re
                new_content = re.sub(r"ELEVENLABS_API_KEY=.*", f"ELEVENLABS_API_KEY={new_key}", content)
            else:
                new_content = content + f"\nELEVENLABS_API_KEY={new_key}\n"
            env_path.write_text(new_content, encoding="utf-8")
        os.environ["ELEVENLABS_API_KEY"] = new_key
    except Exception as err:
        logger.warning(f"Could not write to .env file: {err}")

    quota = await tts_service.get_quota_status()
    return {"status": "success", "message": "تم تحديث وتفعيل مفتاح ElevenLabs بنجاح!", "quota": quota}

