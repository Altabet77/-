import os
import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ai.orchestrator import orchestrator
from app.core.config import settings, BASE_DIR

logger = logging.getLogger("samir.api.providers")
router = APIRouter(prefix="/providers", tags=["AI Providers & Models"])

ENV_FILE_PATH = BASE_DIR / ".env"


class SetDefaultProviderRequest(BaseModel):
    provider: str


class SaveApiKeysRequest(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    qwen_api_key: Optional[str] = None
    qwen_base_url: Optional[str] = None
    default_provider: Optional[str] = None
    claude_model: Optional[str] = None
    openai_model: Optional[str] = None
    qwen_model: Optional[str] = None
    duckai_model: Optional[str] = None
    duckai_enabled: Optional[bool] = None


class TestProviderRequest(BaseModel):
    provider: str


def _update_env_file(key_values: Dict[str, str]):
    """تحديث أو كتابة متغيرات البيئة في ملف .env مع الحفاظ على التنسيق والتعليقات"""
    lines = []
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    keys_written = set()
    new_lines = []

    for line in lines:
        matched_key = None
        for k in key_values.keys():
            if re.match(rf"^\s*{re.escape(k)}\s*=", line):
                matched_key = k
                break

        if matched_key:
            val = key_values[matched_key]
            new_lines.append(f"{matched_key}={val}\n")
            keys_written.add(matched_key)
        else:
            new_lines.append(line)

    # إضافة المفاتيح التي لم تكن موجودة في الملف
    for k, v in key_values.items():
        if k not in keys_written and v is not None:
            new_lines.append(f"{k}={v}\n")

    with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


@router.get("")
async def get_providers_status():
    """الحصول على قائمة جميع المزودين وحالة كل مزود (مفعل/غير مفعل)"""
    return orchestrator.get_available_providers_info()


@router.post("/set-default")
async def set_default_provider(req: SetDefaultProviderRequest):
    """تحديد المزود الافتراضي الفوري للمحادثات"""
    provider_name = req.provider.lower().strip()
    if provider_name not in ["groq", "gemini", "claude", "openai", "qwen", "duckai", "auto"]:
        raise HTTPException(status_code=400, detail="المزود غير صالح. الخيارات: auto, groq, gemini, claude, openai, qwen, duckai")

    settings.DEFAULT_AI_PROVIDER = provider_name
    _update_env_file({"DEFAULT_AI_PROVIDER": provider_name})
    return {
        "status": "success",
        "default_provider": provider_name,
        "message": f"تم تعيين {provider_name} كمزود افتراضي لسمير بنجاح."
    }


@router.post("/keys")
async def save_api_keys(req: SaveApiKeysRequest):
    """حفظ وتحديث مفاتيح API لجميع المزودين وتطبيقها فورياً"""
    updates_for_env = {}

    if req.groq_api_key is not None:
        key = req.groq_api_key.strip()
        settings.GROQ_API_KEY = key
        updates_for_env["GROQ_API_KEY"] = key

    if req.gemini_api_key is not None:
        key = req.gemini_api_key.strip()
        settings.GEMINI_API_KEY = key
        updates_for_env["GEMINI_API_KEY"] = key

    if req.anthropic_api_key is not None:
        key = req.anthropic_api_key.strip()
        settings.ANTHROPIC_API_KEY = key
        settings.CLAUDE_API_KEY = key
        updates_for_env["ANTHROPIC_API_KEY"] = key
        updates_for_env["CLAUDE_API_KEY"] = key

    if req.openai_api_key is not None:
        key = req.openai_api_key.strip()
        settings.OPENAI_API_KEY = key
        updates_for_env["OPENAI_API_KEY"] = key

    if req.openai_base_url is not None:
        url = req.openai_base_url.strip()
        settings.OPENAI_BASE_URL = url
        updates_for_env["OPENAI_BASE_URL"] = url

    if req.qwen_api_key is not None:
        key = req.qwen_api_key.strip()
        settings.QWEN_API_KEY = key
        updates_for_env["QWEN_API_KEY"] = key

    if req.qwen_base_url is not None:
        url = req.qwen_base_url.strip()
        settings.QWEN_BASE_URL = url
        updates_for_env["QWEN_BASE_URL"] = url

    if req.claude_model:
        settings.CLAUDE_MODEL = req.claude_model.strip()
        updates_for_env["CLAUDE_MODEL"] = req.claude_model.strip()

    if req.openai_model:
        settings.OPENAI_MODEL = req.openai_model.strip()
        updates_for_env["OPENAI_MODEL"] = req.openai_model.strip()

    if req.qwen_model:
        settings.QWEN_MODEL = req.qwen_model.strip()
        updates_for_env["QWEN_MODEL"] = req.qwen_model.strip()

    if req.duckai_model:
        settings.DUCKAI_MODEL = req.duckai_model.strip()
        updates_for_env["DUCKAI_MODEL"] = req.duckai_model.strip()

    if req.duckai_enabled is not None:
        settings.DUCKAI_ENABLED = req.duckai_enabled
        updates_for_env["DUCKAI_ENABLED"] = "true" if req.duckai_enabled else "false"

    if req.default_provider:
        dp = req.default_provider.lower().strip()
        if dp in ["groq", "gemini", "claude", "openai", "qwen", "duckai"]:
            settings.DEFAULT_AI_PROVIDER = dp
            updates_for_env["DEFAULT_AI_PROVIDER"] = dp

    if updates_for_env:
        _update_env_file(updates_for_env)

    # إعادة تحميل المزودين في الذاكرة لتطبيق التغييرات فوراً
    orchestrator.reload_providers()

    return {
        "status": "success",
        "message": "تم حفظ وتفعيل مفاتيح الذكاء الاصطناعي بنجاح!",
        "info": orchestrator.get_available_providers_info()
    }


@router.post("/test")
async def test_provider(req: TestProviderRequest):
    """اختبار سريع لعمل المزود واستجابته"""
    provider_name = req.provider.lower().strip()
    try:
        provider = orchestrator.get_provider(provider_name)
        test_messages = [
            {"role": "user", "content": "مرحباً سمير، أجب بكلمة واحدة فقط: جاهز"}
        ]
        resp = await provider.generate_response(test_messages, temperature=0.2)
        return {
            "status": "success",
            "provider": resp.get("provider", provider_name),
            "model": resp.get("model", "unknown"),
            "reply": resp.get("content", "").strip(),
        }
    except Exception as e:
        logger.error(f"Error testing provider {provider_name}: {e}")
        return {
            "status": "error",
            "provider": provider_name,
            "error": str(e)
        }
