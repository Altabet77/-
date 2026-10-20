import json
import base64
import asyncio
import logging
import aiosqlite
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ai.orchestrator import orchestrator
from app.voice.stt_service import stt_service
from app.voice.tts_service import tts_service
from app.memory.memory_manager import memory_manager
from app.memory.long_term import current_user_var
from app.tools.base_tool import tool_registry
from app.core.config import settings

logger = logging.getLogger("samir.ws")
router = APIRouter()


class ConnectionHub:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.device_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, device_id: str = "web_console"):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.device_connections[device_id] = websocket
        logger.info(f"WebSocket connected: {device_id} (Total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket, device_id: str = "web_console"):
        self.active_connections.discard(websocket)
        if device_id in self.device_connections and self.device_connections[device_id] == websocket:
            del self.device_connections[device_id]
        logger.info(f"WebSocket disconnected: {device_id}")

    async def broadcast(self, message: dict):
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
            except Exception:
                pass


hub = ConnectionHub()
session_voices: Dict[str, str] = {}
session_users: Dict[str, dict] = {}  # session_id -> {user_id, name, ...}
session_voice_mode: Dict[str, bool] = {}  # session_id -> True=voice, False=text
session_device_ids: Dict[str, str] = {}  # session_id -> device_id


async def _send_tts_streaming(websocket: WebSocket, text: str, voice: Optional[str] = None):
    """توليد وبث الصوت جملةً جملةً لأقل تأخر ممكن (Streaming TTS)"""
    try:
        await websocket.send_json({"type": "state", "state": "speaking"})

        # تقسيم النص إلى جمل للبث المتدفق
        import re
        sentences = re.split(r'(?<=[.!?؟،\n])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            sentences = [text]

        for sentence in sentences:
            if not sentence:
                continue
            try:
                audio_bytes = await tts_service.generate_speech_bytes(sentence, voice=voice)
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "audio": audio_b64,
                        "text_chunk": sentence,
                    })
                    # تأخير صغير بين الجمل لتجنب التشابك
                    await asyncio.sleep(0.05)
            except Exception as chunk_err:
                logger.warning(f"TTS chunk error for sentence: {chunk_err}")
                continue

    except Exception as e:
        logger.error(f"Streaming TTS error: {e}")
    finally:
        try:
            await websocket.send_json({"type": "state", "state": "idle"})
        except Exception:
            pass


async def _send_tts_and_idle(websocket: WebSocket, text: str, voice: Optional[str] = None):
    """إرسال صوت كامل للجمل القصيرة (Fallback)"""
    try:
        await websocket.send_json({"type": "state", "state": "speaking"})
        audio_bytes = await tts_service.generate_speech_bytes(text, voice=voice)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await websocket.send_json({"type": "audio_data", "audio": audio_b64})
    except Exception as e:
        logger.error(f"TTS error: {e}")
    finally:
        try:
            await websocket.send_json({"type": "state", "state": "idle"})
        except Exception:
            pass


async def _process_text(websocket: WebSocket, user_text: str, session_id: str, attachments=None, provider=None, voice: Optional[str] = None, send_tts: bool = True):
    """معالجة نص المستخدم عبر Samir Core مع بث الرد تدريجياً فور توليده"""
    await websocket.send_json({"type": "state", "state": "thinking"})

    user_info = session_users.get(session_id)
    c_token = current_user_var.set(user_info)
    context = await memory_manager.get_full_context(session_id, user_text)
    # إضافة ذكريات المستخدم الشخصية إن وُجد مستخدم مسجل
    if user_info:
        user_id = user_info.get("id")
        if user_id:
            try:
                async with aiosqlite.connect(settings.DB_PATH) as _db:
                    _db.row_factory = aiosqlite.Row
                    _cur = await _db.execute(
                        "SELECT key, value FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC LIMIT 30",
                        (user_id,)
                    )
                    user_facts = await _cur.fetchall()
                    for uf in user_facts:
                        context["facts"].insert(0, dict(uf))
            except Exception:
                pass
    available_tools = tool_registry.get_core_tool_schemas()

    try:
        ai_resp = await orchestrator.process_user_input(
            user_text=user_text,
            chat_history=context["history"],
            memory_facts=context["facts"],
            available_tools=available_tools,
            provider_name=provider,
            session_id=session_id,
            attachments=attachments,
        )
    except Exception as e:
        logger.error(f"Orchestrator error: {e}", exc_info=True)
        err_msg = "عذراً يا غالي، صار خطأ في المعالجة. جرب مرة ثانية."
        await websocket.send_json({"type": "response_text", "text": err_msg})
        if send_tts:
            await _send_tts_and_idle(websocket, err_msg)
        else:
            await websocket.send_json({"type": "state", "state": "idle"})
        return

    reply_text = ai_resp.get("content", "")
    tool_calls = ai_resp.get("tool_calls", [])
    needs_confirmation = ai_resp.get("needs_confirmation")

    # إرسال تفاصيل الأدوات المنفذة للواجهة
    if tool_calls:
        await websocket.send_json({
            "type": "tool_calls",
            "tool_calls": tool_calls,
        })
        for tc in tool_calls:
            tc_res = tc.get("result", {})
            if isinstance(tc_res, dict) and tc_res.get("action"):
                await websocket.send_json({
                    "type": "client_action",
                    "action": tc_res["action"],
                    "data": tc_res
                })

    # طلب تأكيد لأمر عالي الخطورة
    if needs_confirmation:
        await websocket.send_json({
            "type": "needs_confirmation",
            "confirmation_id": needs_confirmation.get("confirmation_id"),
            "tool_name": needs_confirmation.get("tool_name"),
            "message": reply_text or needs_confirmation.get("message"),
        })
        if send_tts:
            await _send_tts_and_idle(websocket, reply_text or needs_confirmation.get("message", ""))
        else:
            await websocket.send_json({"type": "state", "state": "idle"})
        return

    final_reply = reply_text or "حاضر، تم التنفيذ."

    # تنظيف وتحويل أي مسار ويندوز محلي في الرد إلى رابط ويب صحيح
    import re
    if final_reply:
        final_reply = re.sub(
            r'[a-zA-Z]:\\[^\s)]*web_console\\generated\\([^\s)]+\.(?:png|jpg|jpeg|webp))',
            r'/static/generated/\1',
            final_reply,
            flags=re.IGNORECASE
        )

    # التأكد من إظهار رابط الصورة المولدة تلقائياً إذا تم استدعاء أداة الرسم
    for tc in tool_calls:
        if tc.get("name") in ["generate_image", "generate_ai_image", "imagine_image"]:
            img_res = tc.get("result", {})
            img_url = img_res.get("image_url") or img_res.get("direct_url")
            prompt_used = img_res.get("prompt") or tc.get("arguments", {}).get("prompt", "صورة")
            if img_url and img_url not in final_reply:
                final_reply += f"\n\n![{prompt_used}]({img_url})"

    user_info = session_users.get(session_id)
    cur_user_id = user_info.get("id") if user_info else None
    cur_dev_id = session_device_ids.get(session_id, "")

    await memory_manager.record_interaction(
        session_id=session_id,
        user_text=user_text,
        assistant_text=final_reply,
        provider=ai_resp.get("provider"),
        model=ai_resp.get("model"),
        routing_reason=ai_resp.get("routing_reason"),
        tool_calls=tool_calls,
        device_id=cur_dev_id,
        user_id=cur_user_id,
    )

    # إرسال الرد النصي كاملاً فوراً (قبل الصوت)
    await websocket.send_json({
        "type": "response_text",
        "text": final_reply,
        "provider": ai_resp.get("provider", "groq"),
        "model": ai_resp.get("model", ""),
        "routing_reason": ai_resp.get("routing_reason"),
        "tool_calls": tool_calls,
    })

    # بث الصوت فقط إذا كان وضع الصوت مفعلاً
    if send_tts:
        if len(final_reply) > 150:
            await _send_tts_streaming(websocket, final_reply, voice=voice)
        else:
            await _send_tts_and_idle(websocket, final_reply, voice=voice)
    else:
        # أرسل state=idle بدون صوت
        await websocket.send_json({"type": "state", "state": "idle"})


@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    query_sid = websocket.query_params.get("session_id")
    header_sid = websocket.headers.get("x-session-id")
    raw_sid = query_sid or header_sid or "default"
    session_id = "ws_voice_session_" + raw_sid
    device_id = websocket.query_params.get("device_id") or websocket.headers.get("x-device-id") or ""
    session_device_ids[session_id] = device_id
    await hub.connect(websocket, device_id=session_id)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "unknown")

            # ── مقاطعة الصوت ─────────────────────────────────────────────
            if msg_type == "abort":
                logger.info("Barge-in signal received.")
                await websocket.send_json({"type": "aborted"})

            # ── ping/pong للحفاظ على الاتصال ────────────────────────────
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            # ── تسجيل دخول المستخدم (Google) ────────────────────────────
            elif msg_type == "set_auth":
                token = msg.get("token", "")
                if token:
                    try:
                        async with aiosqlite.connect(settings.DB_PATH) as _db:
                            _db.row_factory = aiosqlite.Row
                            _cur = await _db.execute(
                                "SELECT id, email, name, picture FROM users WHERE session_token = ?",
                                (token,)
                            )
                            user_row = await _cur.fetchone()
                        if user_row:
                            session_users[session_id] = dict(user_row)
                            await websocket.send_json({
                                "type": "auth_ok",
                                "user": dict(user_row)
                            })
                            logger.info(f"Session {session_id} authenticated as user: {user_row['email']}")
                        else:
                            await websocket.send_json({"type": "auth_error", "message": "Invalid token"})
                    except Exception as auth_err:
                        logger.error(f"Auth error: {auth_err}")
                        await websocket.send_json({"type": "auth_error", "message": str(auth_err)})

            # ── تغيير وضع الصوت ──────────────────────────────────────────
            elif msg_type == "set_voice_mode":
                is_voice = msg.get("enabled", False)
                session_voice_mode[session_id] = is_voice
                await websocket.send_json({"type": "voice_mode_updated", "enabled": is_voice})

            # ── تغيير الصوت المباشر للجلسة ──────────────────────────────
            elif msg_type == "select_voice":
                new_v = msg.get("voice", "")
                if new_v:
                    session_voices[session_id] = new_v
                    tts_service.set_voice(new_v)
                    logger.info(f"Session {session_id} voice updated to: {new_v}")
                    await websocket.send_json({"type": "voice_updated", "voice": new_v})

            # ── نص مباشر — بدون TTS ما لم يكن وضع الصوت مفعلاً ────────
            elif msg_type == "text_input":
                user_text = msg.get("text", "").strip()
                attachments = msg.get("attachments", None)
                provider = msg.get("provider", None)
                voice = msg.get("voice") or session_voices.get(session_id) or tts_service.voice
                if voice:
                    session_voices[session_id] = voice
                # TTS فقط إذا كان وضع الصوت مفعلاً
                tts_enabled = session_voice_mode.get(session_id, False)
                if user_text:
                    await _process_text(websocket, user_text, session_id, attachments=attachments, provider=provider, voice=voice, send_tts=tts_enabled)

            # ── صوت Base64 — دائماً مع TTS ────────────────────────────────
            elif msg_type == "audio_input":
                audio_b64 = msg.get("audio") or msg.get("audio_b64") or ""
                voice = msg.get("voice") or session_voices.get(session_id) or tts_service.voice
                if voice:
                    session_voices[session_id] = voice
                if not audio_b64:
                    continue

                await websocket.send_json({"type": "state", "state": "transcribing"})
                audio_bytes = base64.b64decode(audio_b64)

                # كشف نوع الملف الصوتي تلقائياً من رأس البيانات (Magic Bytes)
                audio_filename = "user_voice.webm"
                if len(audio_bytes) >= 4:
                    # MP4/M4A: ftyp header at bytes 4-8
                    if audio_bytes[4:8] in (b"ftyp", b"isom", b"mp42", b"M4A "):
                        audio_filename = "user_voice.mp4"
                    # WAV: RIFF header
                    elif audio_bytes[:4] == b"RIFF":
                        audio_filename = "user_voice.wav"
                    # MP3: ID3 or frame sync
                    elif audio_bytes[:3] == b"ID3" or (audio_bytes[0] == 0xFF and audio_bytes[1] & 0xE0 == 0xE0):
                        audio_filename = "user_voice.mp3"
                    # OGG: OggS header
                    elif audio_bytes[:4] == b"OggS":
                        audio_filename = "user_voice.ogg"

                transcribed_text = await stt_service.transcribe_audio(
                    audio_bytes=audio_bytes,
                    filename=audio_filename,
                )

                await websocket.send_json({
                    "type": "transcription",
                    "text": transcribed_text,
                })

                if transcribed_text:
                    await _process_text(websocket, transcribed_text, session_id, voice=voice)
                else:
                    await websocket.send_json({"type": "state", "state": "idle"})

            # ── تأكيد أمر عالي الخطورة ───────────────────────────────────
            elif msg_type == "confirm_action":
                confirmation_id = msg.get("confirmation_id", "")
                if not confirmation_id:
                    continue

                result = await tool_registry.confirm_and_execute(confirmation_id)
                status = result.get("status", "unknown")

                if status == "success":
                    reply = "تم تنفيذ الأمر بنجاح."
                elif status == "error":
                    reply = result.get("message", "حدث خطأ أثناء التنفيذ.")
                else:
                    reply = result.get("message", "تم.")

                await websocket.send_json({
                    "type": "response_text",
                    "text": reply,
                    "confirmation_result": result,
                })
                await _send_tts_and_idle(websocket, reply)

            # ── رفض أمر عالي الخطورة ─────────────────────────────────────
            elif msg_type == "reject_action":
                confirmation_id = msg.get("confirmation_id", "")
                if not confirmation_id:
                    continue

                result = await tool_registry.reject_confirmation(confirmation_id)
                reply = result.get("message", "تم إلغاء الأمر.")

                await websocket.send_json({
                    "type": "response_text",
                    "text": reply,
                })
                await _send_tts_and_idle(websocket, reply)

    except WebSocketDisconnect:
        session_voices.pop(session_id, None)
        session_users.pop(session_id, None)
        session_voice_mode.pop(session_id, None)
        hub.disconnect(websocket, device_id=session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        session_voices.pop(session_id, None)
        session_users.pop(session_id, None)
        session_voice_mode.pop(session_id, None)
        hub.disconnect(websocket, device_id=session_id)
