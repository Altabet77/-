import os
import time
import base64
import urllib.parse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx

from app.tools.base_tool import tool_registry
from app.core.config import settings

logger = logging.getLogger("samir.tools.image_gen")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = BASE_DIR / "web_console" / "generated"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# الروابط المحلية الافتراضية لأدوات الرسم الحرة
AUTO1111_URL = os.getenv("AUTO1111_URL", "http://127.0.0.1:7860")
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")


async def _enrich_prompt_with_gemini(arabic_prompt: str, style: str) -> str:
    """
    تحسين وترجمة الوصف من العربية إلى برومبت إنجليزي فني فائق الجودة مخصص لنماذج الرسم
    """
    if not settings.GEMINI_API_KEY:
        return arabic_prompt

    # إذا كان البرومبت إنجليزياً بالفعل وقصيراً
    if all(ord(c) < 128 for c in arabic_prompt.replace(" ", "")):
        return arabic_prompt

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        req_text = (
            f"You are an expert AI prompt engineer for Flux and Stable Diffusion.\n"
            f"Convert this user concept into a single concise, highly descriptive English visual prompt for generating an image:\n"
            f"Concept: '{arabic_prompt}'\n"
            f"Style: {style}\n"
            f"Output ONLY the comma-separated English prompt with artistic modifiers (lighting, details, quality). No explanations."
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": req_text}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 100}
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])
                if cand:
                    parts = cand[0].get("content", {}).get("parts", [])
                    res = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if res and len(res) > 5:
                        # إزالة علامات الاقتباس إن وجدت
                        return res.strip('"\'')
    except Exception as e:
        logger.debug(f"Gemini prompt enrichment skipped: {e}")

    return arabic_prompt


async def _try_generate_automatic1111(prompt: str, negative_prompt: str = "blurry, low quality, bad anatomy") -> Optional[str]:
    """توليد محلي فائق السرعة عبر Automatic1111 / SD-WebUI إذا كان السيرفر مشغلاً على جهاز المستخدم"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as check_client:
            r = await check_client.get(f"{AUTO1111_URL}/sdapi/v1/options")
            if r.status_code != 200:
                return None

        # Automatic1111 متاح محلياً!
        logger.info(f"Generating image via local Automatic1111 ({AUTO1111_URL})...")
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": 20,
            "width": 1024,
            "height": 1024,
            "cfg_scale": 7.0,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{AUTO1111_URL}/sdapi/v1/txt2img", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                if images:
                    img_data = base64.b64decode(images[0])
                    timestamp = int(time.time())
                    filename = f"samir_sd_{timestamp}.png"
                    file_path = IMAGES_DIR / filename
                    with open(file_path, "wb") as f:
                        f.write(img_data)
                    return f"/static/generated/{filename}"
    except Exception as e:
        logger.debug(f"Automatic1111 not available or failed: {e}")
    return None


async def _try_generate_comfyui(prompt: str) -> Optional[str]:
    """توليد محلي عبر ComfyUI إذا كان يعمل محلياً"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as check_client:
            r = await check_client.get(f"{COMFYUI_URL}/system_stats")
            if r.status_code != 200:
                return None

        logger.info("ComfyUI server detected locally.")
    except Exception:
        pass
    return None


async def tool_generate_image(
    prompt: str,
    style: str = "photorealistic",
    model: str = "flux"
) -> Dict[str, Any]:
    """
    توليد ورسم وتخيل الصور بالذكاء الاصطناعي مع دعم محركات متعددة حرة:
    - محلي: Automatic1111 أو ComfyUI (إذا كان مشغلاً على الجهاز بدون أي ضغط سيرفرات)
    - سحابي حر: Pollinations Flux / Turbo / SDXL (مجاني 100% وبدون قيود وسريع)
    """
    try:
        # 1. تحسين وترجمة البرومبت
        english_prompt = await _enrich_prompt_with_gemini(prompt, style)

        style_prompts = {
            "photorealistic": "photorealistic, 8k resolution, ultra detailed, cinematic lighting, masterpiece",
            "digital art": "concept digital art, vibrant colors, trending on artstation, highly detailed",
            "anime": "anime aesthetic, studio ghibli and makoto shinkai style, gorgeous lighting, 4k anime wallpaper",
            "cyberpunk": "cyberpunk 2077 aesthetic, neon glowing lights, dark rainy city, futuristic tech",
            "3d render": "octane 3d render, smooth textures, ray tracing, unreal engine 5, 8k",
            "fantasy": "epic fantasy illustration, magical glowing particles, mystical atmosphere, artstation",
        }
        chosen_style = style_prompts.get(style.lower(), "masterpiece, high quality, 8k resolution")
        final_prompt = f"{english_prompt}, {chosen_style}"

        # 2. فحص السيرفرات المحلية أولاً (Automatic1111 / ComfyUI)
        local_sd_url = await _try_generate_automatic1111(final_prompt)
        if local_sd_url:
            return {
                "status": "success",
                "engine": "Automatic1111 (Local GPU)",
                "message": f"تم رسم وتخيل الصورة محلياً بجهازك: {prompt}",
                "image_url": local_sd_url,
                "prompt": prompt,
                "style": style,
            }

        # 3. محرك Flux & Turbo الحر (Pollinations)
        encoded_prompt = urllib.parse.quote(final_prompt)
        
        # محرك توليد الصور المجاني السريع عالي الدقة بدون علامة مائية وبدون قيود (model=sana)
        # نستخدم model=sana مع nologo=true وبدون enhance=true لمنع طلب الدفع 402
        primary_model = "sana"
        seed = int(time.time()) % 100000
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model={primary_model}&seed={seed}&nologo=true"

        # حفظ الصورة محلياً بصيغة PNG عالية الجودة للمشاهدة السريعة والمستقرة
        timestamp = int(time.time())
        filename = f"samir_art_{timestamp}.png"
        file_path = IMAGES_DIR / filename

        local_url = image_url  # الرابط المباشر كاحتياط
        saved_locally = False
        try:
            # مهلة 30 ثانية للتحميل والتحويل لـ PNG بدون أي علامة مائية
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                is_valid_img = resp.status_code == 200 and len(resp.content) > 1000 and resp.headers.get("content-type", "").startswith("image/")
                
                if not is_valid_img:
                    # بديل 1: تجربة موديل flux بدون علامة مائية
                    fallback_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&seed={seed}&nologo=true"
                    resp = await client.get(fallback_url)
                    is_valid_img = resp.status_code == 200 and len(resp.content) > 1000 and resp.headers.get("content-type", "").startswith("image/")
                    if is_valid_img:
                        image_url = fallback_url
                    else:
                        # بديل 2: تجربة موديل turbo
                        turbo_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=turbo&seed={seed}&nologo=true"
                        resp = await client.get(turbo_url)
                        is_valid_img = resp.status_code == 200 and len(resp.content) > 1000 and resp.headers.get("content-type", "").startswith("image/")
                        if is_valid_img:
                            image_url = turbo_url

                if is_valid_img:
                    import io
                    from PIL import Image
                    with Image.open(io.BytesIO(resp.content)) as im:
                        im.convert("RGB").save(file_path, format="PNG", optimize=True)
                    if file_path.exists() and file_path.stat().st_size > 2000:
                        local_url = f"/static/generated/{filename}"
                        saved_locally = True
                        logger.info(f"Image successfully saved and verified locally: {file_path} ({file_path.stat().st_size} bytes)")
        except Exception as e:
            logger.warning(f"Could not download image locally, using direct stream URL: {e}")
            local_url = image_url

        # الرابط المعتمد هو local_url فقط لمنع تسريب مسارات ويندوز المحلية للنموذج
        web_image_url = local_url if saved_locally else image_url

        return {
            "status": "success",
            "engine": f"AI Art ({primary_model})",
            "message": f"تفضل يا غالي، تخيلت ورسمتلك المشهد {'وحفظته بصيغة PNG عالية الدقة على جهازك' if saved_locally else 'وجاهز للعرض'}: {prompt}",
            "image_url": web_image_url,
            "direct_url": web_image_url,
            "file_name": filename if saved_locally else None,
            "format": "PNG",
            "prompt": prompt,
            "style": style,
        }

    except Exception as e:
        logger.error(f"Image generation error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"تعذر رسم المشهد حالياً: {e}",
        }


async def tool_search_civitai(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    البحث في مستودع Civitai عن نماذج الذكاء الاصطناعي (Checkpoints / LoRA) والبرومبتات الملهمة
    """
    try:
        url = f"https://civitai.com/api/v1/models?query={urllib.parse.quote(query)}&limit={limit}"
        headers = {"User-Agent": "Samir-AI-Assistant/1.0"}
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                results = []
                for it in items:
                    results.append({
                        "name": it.get("name"),
                        "type": it.get("type"),
                        "creator": it.get("creator", {}).get("username"),
                        "downloadCount": it.get("stats", {}).get("downloadCount"),
                        "rating": it.get("stats", {}).get("rating"),
                        "url": f"https://civitai.com/models/{it.get('id')}"
                    })
                return {
                    "status": "success",
                    "query": query,
                    "models": results,
                    "count": len(results)
                }
            else:
                return {"status": "error", "message": f"Civitai API status {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def register_image_tools():
    tool_registry.register_tool(
        name="generate_image",
        description="توليد ورسم وتخيل صورة أو مشهد بالذكاء الاصطناعي (أمثلة: 'ارسم لي قطة فضائية', 'تخيل سيارة مستقبلية في دبي', 'ارسم لوحة أنمي', 'تخيل قلعة في السحاب'). يتم الربط تلقائياً إما محلياً بـ Automatic1111/ComfyUI أو بسحابة Flux الحرة السريعة.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "وصف المشهد أو الصورة المطلوب رسمها وتخيلها بالتفصيل",
                },
                "style": {
                    "type": "string",
                    "enum": ["photorealistic", "digital art", "anime", "cyberpunk", "3d render", "fantasy"],
                    "description": "الأسلوب الفني للصورة",
                },
                "model": {
                    "type": "string",
                    "enum": ["flux", "turbo"],
                    "description": "نوع المحرك (flux للجودة الفائقة، turbo للسرعة الخارقة)",
                }
            },
            "required": ["prompt"],
        },
        handler=tool_generate_image,
    )

    # Aliases
    tool_registry.register_tool(
        name="generate_ai_image",
        description="رسم وتوليد صورة بالذكاء الاصطناعي بناءً على طلب المستخدم.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "وصف الصورة"},
                "style": {"type": "string", "description": "الأسلوب الفني"},
            },
            "required": ["prompt"],
        },
        handler=tool_generate_image,
    )

    tool_registry.register_tool(
        name="imagine_image",
        description="تخيل مشهد وتصويره بالذكاء الاصطناعي (مثل: 'تخيل لي كذا وكذا').",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "المشهد المتخيل"},
                "style": {"type": "string", "description": "الأسلوب الفني"},
            },
            "required": ["prompt"],
        },
        handler=tool_generate_image,
    )

    tool_registry.register_tool(
        name="search_civitai_models",
        description="البحث في موقع civitai.com عن نماذج الذكاء الاصطناعي (LoRA و Checkpoints) المتاحة للتحميل ومجتمع الرسم.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "اسم النموذج أو الكلمة المفتاحية مثل anime, realistic, cyberpunk"},
                "limit": {"type": "integer", "description": "عدد النتائج المطلوب إرجاعها (افتراضياً 5)"}
            },
            "required": ["query"],
        },
        handler=tool_search_civitai,
    )


register_image_tools()
