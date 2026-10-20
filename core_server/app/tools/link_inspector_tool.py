"""
link_inspector_tool.py — سمير: فحص وقراءة روابط إنستغرام، يوتيوب، ومواقع الويب
يستخرج العناوين، الوصف، النصوص، والمحتوى لمناقشته مع المستخدم بذكاء
"""

import re
import json
import logging
import urllib.parse
from typing import Dict, Any, Optional

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.link_inspector")


async def tool_inspect_url(url: str) -> Dict[str, Any]:
    """
    الدخول على أي رابط موقع أو منشور إنستغرام أو فيديو يوتيوب وقراءة محتواه، نصوصه، ووصفه.
    url: الرابط المراد فحصه (Instagram, YouTube, Twitter/X, أو أي صفحة ويب)
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    parsed = urllib.parse.urlparse(clean_url)
    domain = parsed.netloc.lower()

    # 1. فحص روابط إنستغرام
    if "instagram.com" in domain:
        return await _inspect_instagram(clean_url)

    # 2. فحص روابط يوتيوب
    if "youtube.com" in domain or "youtu.be" in domain:
        return await _inspect_youtube(clean_url)

    # 3. فحص روابط الويب العامة
    return await _inspect_general_webpage(clean_url)


async def _inspect_instagram(url: str) -> Dict[str, Any]:
    """استخراج بيانات ووصف منشور أو ريلز إنستغرام"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ar,en;q=0.9",
    }
    
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # استخراج OpenGraph Tags
        title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
        desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
        img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)

        title = title_match.group(1) if title_match else "منشور إنستغرام"
        caption = desc_match.group(1) if desc_match else ""
        image_url = img_match.group(1) if img_match else ""

        # فك رموز HTML Entities
        import html as html_lib
        title = html_lib.unescape(title)
        caption = html_lib.unescape(caption)

        return {
            "status": "success",
            "platform": "Instagram",
            "url": url,
            "title": title,
            "caption": caption or "منشور إنستغرام (محتوى مرئي)",
            "thumbnail_url": image_url,
            "message": f"تم جلب بيانات المنشور من إنستغرام: {title}\nالوصف والنص: {caption}",
        }
    except Exception as e:
        logger.warning(f"Fast HTTP failed for Instagram {url}: {e}, trying Playwright...")
        # محاولة بالمتصفح إن فشل الطلب المباشر
        try:
            from app.tools.browser_automation_tool import tool_browser_navigate, tool_browser_get_page_text
            nav_res = await tool_browser_navigate(url, headless=True)
            text_res = await tool_browser_get_page_text()
            return {
                "status": "success",
                "platform": "Instagram",
                "url": url,
                "title": text_res.get("title", "Instagram Post"),
                "content": text_res.get("content_preview", ""),
                "message": "تم فتح المنشور وقراءة المحتوى عبر المتصفح.",
            }
        except Exception as browser_err:
            return {
                "status": "partial",
                "platform": "Instagram",
                "url": url,
                "message": f"الرابط يخص إنستغرام: {url}. قد يتطلب تسجيل الدخول لعرض التفاصيل الكاملة.",
            }


async def _inspect_youtube(url: str) -> Dict[str, Any]:
    """استخراج بيانات فيديو يوتيوب"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        title_match = re.search(r'<meta\s+name=["\']title["\']\s+content=["\'](.*?)["\']', html)
        desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html)

        import html as html_lib
        title = html_lib.unescape(title_match.group(1)) if title_match else "فيديو يوتيوب"
        desc = html_lib.unescape(desc_match.group(1)) if desc_match else ""

        return {
            "status": "success",
            "platform": "YouTube",
            "url": url,
            "title": title,
            "description": desc,
            "message": f"فيديو يوتيوب: {title}\nالوصف: {desc[:500]}",
        }
    except Exception as e:
        return {"status": "error", "message": f"تعذر قراءة فيديو يوتيوب: {e}"}


async def _inspect_general_webpage(url: str) -> Dict[str, Any]:
    """استخراج محتوى ونصوص أي صفحة ويب عامة"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar,en;q=0.9",
    }
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # استخراج العنوان
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        import html as html_lib
        title = html_lib.unescape(title_match.group(1).strip()) if title_match else "صفحة ويب"

        # إزالة وسوم Script و Style
        clean_html = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', ' ', html, flags=re.IGNORECASE | re.DOTALL)
        # إزالة وسوم HTML
        text = re.sub(r'<[^>]+>', ' ', clean_html)
        text = " ".join(text.split())

        preview = text[:3000]

        return {
            "status": "success",
            "platform": "Web",
            "url": url,
            "title": title,
            "content_preview": preview,
            "total_chars": len(text),
            "message": f"تم الدخول على الصفحة: {title}\nمقتطف من المحتوى: {preview[:400]}...",
        }
    except Exception as e:
        logger.warning(f"Error inspecting web page {url}: {e}")
        return {"status": "error", "message": f"تعذر الدخول على الصفحة وقراءتها: {e}"}


# ── التسجيل في سجل الأدوات المركزي لسمير ──────────────────────────────────
tool_registry.register(
    name="inspect_url",
    func=tool_inspect_url,
    schema={
        "name": "inspect_url",
        "description": "ادخل على أي رابط يقدمه المستخدم (رابط إنستغرام، يوتيوب، مقال، أو صفحة ويب) واقرأ محتواه ووصفه وتفاصيله لتشاهده وتناقشه معه بدقة.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "رابط الصفحة أو المنشور (مثال: https://www.instagram.com/p/...)"
                }
            },
            "required": ["url"]
        }
    }
)
