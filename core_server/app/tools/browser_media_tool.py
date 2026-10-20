import os
import sys
import webbrowser
import subprocess
import urllib.parse
import logging
import re
from typing import Dict, Any, Optional

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.browser_media")


def get_default_browser_exe() -> Optional[str]:
    candidates = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


async def tool_open_browser_tab(url: str) -> Dict[str, Any]:
    """
    فتح رابط أو موقع إلكتروني في تاب جديد بمتصفح Brave (أو المتصفح الافتراضي).
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    logger.info(f"Opening browser tab: {clean_url}")

    browser = get_default_browser_exe()
    is_brave = browser and "brave" in browser.lower()
    browser_label = "Brave" if is_brave else "المتصفح"

    if browser and os.path.exists(browser):
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([browser, clean_url], creationflags=creationflags)
            return {
                "status": "success",
                "message": f"فتحتلك الموقع في متصفح {browser_label} بنجاح: {clean_url} 🚀",
                "url": clean_url,
                "browser": browser_label,
            }
        except Exception as e:
            logger.warning(f"Direct browser launch failed: {e}")
            try:
                ps_cmd = f"Start-Process '{browser}' -ArgumentList '{clean_url}'"
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, timeout=5)
                return {
                    "status": "success",
                    "message": f"فتحتلك الموقع في متصفح {browser_label} بنجاح: {clean_url} 🚀",
                    "url": clean_url,
                    "browser": browser_label,
                }
            except Exception as pe:
                logger.warning(f"PowerShell browser launch failed: {pe}")

    webbrowser.open_new_tab(clean_url)
    return {
        "status": "success",
        "message": f"تم فتح الرابط في المتصفح: {clean_url} 🚀",
        "url": clean_url,
        "browser": browser_label,
    }


async def tool_search_youtube(query: str, in_browser: bool = False) -> Dict[str, Any]:
    """
    البحث في يوتيوب وتشغيله مباشرة داخل مشغل سمير المدمج (In-App Player)،
    أو فتحه في متصفح Brave فقط إذا طلب المستخدم صراحة 'في المتصفح'.
    """
    q_lower = query.lower()
    browser_triggers = ["المتصفح", "متصفح", "البرايف", "برايف", "البراف", "براف", "brave", "browser", "الكروم", "كروم", "chrome", "نافذة جديدة", "تاب خارجي"]
    wants_browser = in_browser or any(t in q_lower for t in browser_triggers)

    # تنظيف العبارة من كلمات الأمر
    clean_q = query
    stop_words = [
        "المتصفح", "متصفح", "البرايف", "برايف", "البراف", "براف", "brave", "browser",
        "الكروم", "كروم", "chrome", "نافذة", "تاب", "tab",
        "اليوتيوب", "يوتيوب", "youtube", "افتح", "شغل", "ابحث", "بحث", "في", "على", "لي", "عن", "مقطع", "فيديو"
    ]
    for sw in stop_words:
        clean_q = re.sub(rf"(?i)\b{re.escape(sw)}\b|\s*{re.escape(sw)}\s*", " ", clean_q)
    clean_q = re.sub(r"\s+", " ", clean_q).strip()

    if clean_q:
        encoded_q = urllib.parse.quote(clean_q)
        yt_target_url = f"https://www.youtube.com/results?search_query={encoded_q}"
    else:
        yt_target_url = "https://www.youtube.com"

    # إذا طلب صراحة فتحه بالمتصفح الخارجي
    if wants_browser:
        logger.info(f"Opening YouTube in external browser: {yt_target_url}")
        res = await tool_open_browser_tab(yt_target_url)
        res["message"] = f"فتحتلك اليوتيوب في متصفح Brave مباشرة! 🎬✨ ({yt_target_url})"
        return res

    logger.info(f"Searching YouTube in-app: query='{query}', clean='{clean_q}'")

    video_id = None
    try:
        import httpx
        # فحص إذا كان المستخدم قد أرسل رابط يوتيوب مباشر
        url_match = re.search(r'(?:v=|\/embed\/|\.be\/)([a-zA-Z0-9_-]{11})', query)
        if url_match:
            video_id = url_match.group(1)
        else:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    yt_target_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "ar,en;q=0.9",
                    }
                )
                if resp.status_code == 200:
                    # استخراج videoId من نتائج البحث
                    match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
                    if not match:
                        match = re.search(r'/watch\?v=([a-zA-Z0-9_-]{11})', resp.text)
                    if match:
                        video_id = match.group(1)
    except Exception as e:
        logger.warning(f"Failed to extract video_id: {e}")

    if video_id:
        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&enablejsapi=1"
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
    else:
        # البديل المدمج الآمن: تشغيل قائمة البحث
        embed_url = f"https://www.youtube.com/embed?listType=search&list={urllib.parse.quote(clean_q or query)}&autoplay=1"
        watch_url = yt_target_url

    title_text = clean_q or query or "فيديو يوتيوب"
    return {
        "status": "success",
        "action": "open_in_app_media",
        "service": "youtube",
        "title": title_text,
        "video_id": video_id or "",
        "embed_url": embed_url,
        "url": watch_url,
        "in_app_player": True,
        "message": f"شغلتلك مقطع اليوتيوب داخل سمير مباشرة 🎬: '{title_text}'",
    }


async def tool_play_spotify(query: str = "", in_browser: bool = False) -> Dict[str, Any]:
    """
    تشغيل الموسيقى، الأغاني، أو البودكاست في سبوتيفاي مباشرة داخل مشغل سمير المدمج (In-App Player).
    """
    q_lower = query.lower()
    browser_triggers = ["المتصفح", "متصفح", "البرايف", "برايف", "البراف", "براف", "brave", "browser", "الكروم", "كروم", "chrome"]
    wants_browser = in_browser or any(t in q_lower for t in browser_triggers)

    clean_q = query
    stop_words = [
        "المتصفح", "متصفح", "البرايف", "برايف", "البراف", "براف", "brave", "browser",
        "سبوتيفاي", "سبوتفاي", "spotify", "افتح", "شغل", "ابحث", "بحث", "في", "على", "لي", "عن", "أغنية", "موسيقى", "بودكاست"
    ]
    for sw in stop_words:
        clean_q = re.sub(rf"(?i)\b{re.escape(sw)}\b|\s*{re.escape(sw)}\s*", " ", clean_q)
    clean_q = re.sub(r"\s+", " ", clean_q).strip()

    title_text = clean_q or query or "Spotify Player"

    # التحقق إن كان الرابط رابط سبوتيفاي مباشر (Track / Album / Playlist)
    if "open.spotify.com" in query:
        # تحويل الرابط إلى embed link
        # e.g. https://open.spotify.com/track/xyz -> https://open.spotify.com/embed/track/xyz
        embed_url = re.sub(r'open\.spotify\.com\/(track|album|playlist|artist|episode)\/', r'open.spotify.com/embed/\1/', query.strip())
        web_url = query.strip()
    elif clean_q:
        encoded_q = urllib.parse.quote(clean_q)
        embed_url = f"https://open.spotify.com/embed/search/{encoded_q}"
        web_url = f"https://open.spotify.com/search/{encoded_q}"
    else:
        embed_url = "https://open.spotify.com/embed"
        web_url = "https://open.spotify.com"

    if wants_browser:
        res = await tool_open_browser_tab(web_url)
        res["message"] = f"فتحتلك سبوتيفاي في المتصفح بنجاح! 🎵 ({web_url})"
        return res

    logger.info(f"Playing Spotify in-app: query='{query}', embed='{embed_url}'")
    return {
        "status": "success",
        "action": "open_in_app_media",
        "service": "spotify",
        "title": title_text,
        "embed_url": embed_url,
        "url": web_url,
        "in_app_player": True,
        "message": f"فتحتلك سبوتيفاي داخل سمير مباشرة 🎵: '{title_text}'",
    }


async def tool_modify_file_content(original_filename: str, new_content: str, summary_of_changes: str) -> Dict[str, Any]:
    """
    تعديل ملف برمجي أو نصي وإنشاء النسخة المحدثة مع رابط تحميل مباشر للمستخدم.
    """
    from app.media.file_processor import file_processor
    res = file_processor.save_modified_file(original_filename, new_content)
    return {
        "status": "success",
        "message": f"عدلتلك الملف '{original_filename}' بنجاح! التغييرات: {summary_of_changes}",
        "filename": res["filename"],
        "download_url": res["url"],
        "lines": res["lines"],
        "summary": summary_of_changes,
    }


async def tool_open_web_service(service: str, extra_query: Optional[str] = None) -> Dict[str, Any]:
    """
    فتح خدمات وتطبيقات الويب الشائعة (youtube, spotify, google, github, twitter, chatgpt).
    تشغل يوتيوب وسبوتيفاي داخل سمير نفسه مباشرة.
    """
    s = service.strip().lower()

    if s in ["youtube", "يوتيوب"]:
        return await tool_search_youtube(extra_query or "")
    elif s in ["spotify", "سبوتيفاي", "سبوتفاي"]:
        return await tool_play_spotify(extra_query or "")

    services_map = {
        "google": "https://www.google.com",
        "github": "https://github.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "chatgpt": "https://chatgpt.com",
        "reddit": "https://www.reddit.com",
        "gmail": "https://mail.google.com",
        "whatsapp": "https://web.whatsapp.com",
        "discord": "https://discord.com/app",
    }

    base_url = services_map.get(s, f"https://www.{s}.com")
    if extra_query:
        if s == "google":
            base_url = f"https://www.google.com/search?q={urllib.parse.quote(extra_query)}"
        elif s == "github":
            base_url = f"https://github.com/search?q={urllib.parse.quote(extra_query)}"

    return await tool_open_browser_tab(base_url)


def register_browser_media_tools():
    tool_registry.register_tool(
        name="open_browser_tab",
        description="فتح رابط أو موقع إلكتروني في تاب جديد بمتصفح Brave (مثل: فتح موقع، فتح رابط).",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "الرابط الكامل المطلوب فتحه"},
            },
            "required": ["url"],
        },
        handler=tool_open_browser_tab,
    )

    tool_registry.register_tool(
        name="search_youtube",
        description="البحث في يوتيوب وتشغيل مقطع الفيديو مباشرة داخل مشغل سمير المدمج (In-App Player داخل الواجهة).",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "اسم الفيديو أو المقطع أو عبارة البحث في يوتيوب"},
                "in_browser": {"type": "boolean", "description": "ضبطها على true فقط إذا طلب المستخدم فتح يوتيوب في متصفح Brave الخارجي"},
            },
            "required": ["query"],
        },
        handler=tool_search_youtube,
    )

    tool_registry.register_tool(
        name="play_spotify",
        description="تشغيل الموسيقى، الأغاني، أو البودكاست في سبوتيفاي مباشرة داخل مشغل سمير المدمج (In-App Player في الواجهة).",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "اسم الأغنية، الفنان، الألبوم، البودكاست، أو رابط سبوتيفاي"},
                "in_browser": {"type": "boolean", "description": "ضبطها على true فقط إذا طلب المستخدم فتح سبوتيفاي في المتصفح الخارجي"},
            },
            "required": ["query"],
        },
        handler=tool_play_spotify,
    )

    tool_registry.register_tool(
        name="modify_file_content",
        description="تعديل محتوى كود أو ملف نصي أرسله المستخدم أو طلب تعديله، وحفظ النسخة المحدثة مع رابط تحميل مباشر.",
        parameters={
            "type": "object",
            "properties": {
                "original_filename": {"type": "string", "description": "اسم الملف الأصلي المراد تعديله"},
                "new_content": {"type": "string", "description": "المحتوى الكامل والجديد للملف بعد التعديل"},
                "summary_of_changes": {"type": "string", "description": "ملخص التعديلات التي قمت بها"},
            },
            "required": ["original_filename", "new_content", "summary_of_changes"],
        },
        handler=tool_modify_file_content,
    )

    tool_registry.register_tool(
        name="open_web_service",
        description="فتح خدمات الويب والمواقع (youtube, spotify, google, github, twitter, chatgpt).",
        parameters={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "اسم الخدمة (youtube, spotify, google, github, twitter, chatgpt, reddit)",
                },
                "extra_query": {"type": "string", "description": "بحث إضافي داخل الخدمة إن وجد (اختياري)"},
            },
            "required": ["service"],
        },
        handler=tool_open_web_service,
    )


register_browser_media_tools()
