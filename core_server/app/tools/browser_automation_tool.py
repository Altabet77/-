import os
import sys
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.browser_automation")

# حالة جلسة المتصفح المشتركة
_playwright = None
_browser = None
_context = None
_active_page = None
_lock = asyncio.Lock()


async def _ensure_browser(headless: bool = False):
    """تهيئة وتشغيل متصفح Playwright والتأكد من وجود صفحة نشطة"""
    global _playwright, _browser, _context, _active_page

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright library is not installed.")
        raise RuntimeError("مكتبة Playwright غير مثبتة حالياً. يمكنك تثبيتها عبر: pip install playwright && playwright install chromium")

    if _playwright is None:
        _playwright = await async_playwright().start()

    if _browser is None or not _browser.is_connected():
        # تشغيل المتصفح (الافتراضي مرئي headed ليشاهد المستخدم أداء سمير مباشرة)
        try:
            _browser = await _playwright.chromium.launch(
                headless=headless,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            logger.warning(f"Failed to launch bundled chromium, trying channel chrome/msedge: {e}")
            try:
                _browser = await _playwright.chromium.launch(
                    channel="msedge",
                    headless=headless,
                    args=["--start-maximized"]
                )
            except Exception:
                _browser = await _playwright.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=["--start-maximized"]
                )

        _context = await _browser.new_context(
            viewport=None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        _active_page = await _context.new_page()

    if _active_page is None or _active_page.is_closed():
        _active_page = await _context.new_page()

    return _active_page


async def tool_browser_navigate(url: str, headless: bool = False) -> Dict[str, Any]:
    """
    الانتقال إلى موقع ويب في المتصفح الآلي.
    url: الرابط المراد فتحه
    headless: فتح بالخلفية بدون نافذة (الافتراضي False ليرى المستخدم العمل)
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    async with _lock:
        try:
            page = await _ensure_browser(headless=headless)
            await page.goto(clean_url, wait_until="domcontentloaded", timeout=25000)
            title = await page.title()
            return {
                "status": "success",
                "message": f"تم فتح الموقع: {title} ({clean_url})",
                "url": page.url,
                "title": title
            }
        except Exception as e:
            logger.error(f"Error navigating to {clean_url}: {e}")
            return {"status": "error", "message": f"تعذر فتح الصفحة: {e}"}


async def tool_browser_type(selector: str, text: str, press_enter: bool = False) -> Dict[str, Any]:
    """
    كتابة نص في حقل أو عنصر داخل المتصفح (مربع بحث، استمارة، حقل إدخال).
    selector: محدد العنصر CSS أو النص الظاهر مثل 'input[type=text]', '#search', 'textarea'
    text: النص المراد كتابته
    press_enter: الضغط على Enter بعد الكتابة
    """
    async with _lock:
        try:
            page = await _ensure_browser()
            # محاولة العثور على العنصر
            try:
                await page.wait_for_selector(selector, timeout=7000)
                await page.fill(selector, text)
            except Exception:
                # محاولة ثانية بالبحث بالـ placeholder أو role
                try:
                    loc = page.get_by_placeholder(selector)
                    await loc.fill(text)
                except Exception:
                    # محاولة ثالثة بالنقر ثم الكتابة بلوحة المفاتيح
                    await page.click(selector, timeout=5000)
                    await page.keyboard.type(text)

            if press_enter:
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1500)

            return {
                "status": "success",
                "message": f"تمت كتابة النص بنجاح في العنصر ({selector}): '{text}'"
            }
        except Exception as e:
            logger.error(f"Error typing in browser: {e}")
            return {"status": "error", "message": f"فشل الكتابة في العنصر {selector}: {e}"}


async def tool_browser_click(selector: str) -> Dict[str, Any]:
    """
    النقر على زر، رابط، أو عنصر في صفحة المتصفح.
    selector: محدد CSS أو نص الزر مثل 'button[type=submit]', 'text=تسجيل الدخول', 'a.nav-link'
    """
    async with _lock:
        try:
            page = await _ensure_browser()
            try:
                await page.click(selector, timeout=8000)
            except Exception:
                # محاولة النقر عبر البحث بالنص الظاهر
                loc = page.get_by_text(selector, exact=False)
                await loc.first.click(timeout=6000)

            await page.wait_for_timeout(1000)
            return {
                "status": "success",
                "message": f"تم النقر على العنصر: {selector}",
                "current_url": page.url
            }
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {e}")
            return {"status": "error", "message": f"فشل النقر على العنصر {selector}: {e}"}


async def tool_browser_get_page_text(selector: Optional[str] = None) -> Dict[str, Any]:
    """
    استخراج وقراءة النص الكامل للصفحة المفتوحة حالياً في المتصفح أو لجزء معين منها.
    selector: اختياري، محدد CSS لحاوية معينة مثل 'article' أو 'main'
    """
    async with _lock:
        try:
            page = await _ensure_browser()
            if selector:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                else:
                    text = "لم يتم العثور على العنصر المحدد."
            else:
                text = await page.inner_text("body")

            clean_text = " ".join(text.split())
            preview = clean_text[:4000]

            return {
                "status": "success",
                "message": "تم استخراج محتوى الصفحة بنجاح.",
                "title": await page.title(),
                "url": page.url,
                "content_preview": preview,
                "total_length": len(clean_text)
            }
        except Exception as e:
            logger.error(f"Error getting page text: {e}")
            return {"status": "error", "message": f"تعذر استخراج نص الصفحة: {e}"}


async def tool_browser_fill_form(fields: Dict[str, str]) -> Dict[str, Any]:
    """
    ملء استمارة ونموذج متعدد الحقول دفعة واحدة في الصفحة.
    fields: قاموس يحتوي محدد الحقل وقيمته، مثل: {"input[name=username]": "ahmed", "input[name=email]": "test@mail.com"}
    """
    async with _lock:
        try:
            page = await _ensure_browser()
            filled = []
            for sel, val in fields.items():
                try:
                    await page.fill(sel, str(val), timeout=4000)
                    filled.append(sel)
                except Exception as fe:
                    logger.warning(f"Could not fill {sel}: {fe}")

            return {
                "status": "success",
                "message": f"تم ملء {len(filled)} من أصل {len(fields)} حقل بنجاح.",
                "filled_fields": filled
            }
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return {"status": "error", "message": f"فشل ملء النموذج: {e}"}


async def tool_browser_execute_script(script: str) -> Dict[str, Any]:
    """
    تنفيذ كود JavaScript مخصص ومباشر داخل صفحة المتصفح المفتوحة وإرجاع النتيجة.
    script: كود الجافاسكربت المراد تنفيذه
    """
    async with _lock:
        try:
            page = await _ensure_browser()
            result = await page.evaluate(script)
            return {
                "status": "success",
                "message": "تم تنفيذ الكود البرمجي في المتصفح بنجاح.",
                "result": result
            }
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return {"status": "error", "message": f"خطأ أثناء تنفيذ الكود في المتصفح: {e}"}


async def tool_browser_screenshot() -> Dict[str, Any]:
    """
    التقاط صورة لشاشة صفحة الويب الحالية في المتصفح وحفظها وإرجاعها كـ Base64.
    """
    import base64
    async with _lock:
        try:
            page = await _ensure_browser()
            screenshots_dir = Path("./data/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            shot_path = screenshots_dir / "browser_latest.png"

            img_bytes = await page.screenshot(path=str(shot_path), full_page=False)
            b64_str = base64.b64encode(img_bytes).decode("utf-8")

            return {
                "status": "success",
                "message": "تم التقاط صورة المتصفح بنجاح.",
                "file_path": str(shot_path.resolve()),
                "image_base64": b64_str,
                "url": page.url
            }
        except Exception as e:
            logger.error(f"Error capturing browser screenshot: {e}")
            return {"status": "error", "message": f"تعذر التقاط صورة المتصفح: {e}"}


async def tool_browser_close() -> Dict[str, Any]:
    """إغلاق المتصفح وجلسة العمل الآلية"""
    global _browser, _context, _active_page, _playwright
    async with _lock:
        try:
            if _browser:
                await _browser.close()
            if _playwright:
                await _playwright.stop()
            _browser = None
            _context = None
            _active_page = None
            _playwright = None
            return {"status": "success", "message": "تم إغلاق المتصفح بنجاح."}
        except Exception as e:
            return {"status": "error", "message": f"خطأ أثناء إغلاق المتصفح: {e}"}


def register_browser_automation_tools():
    """تسجيل أدوات أتمتة المتصفح في السجل المركزي لسمير"""

    # 1. فتح وتوجيه المتصفح
    tool_registry.register_tool(
        name="browser_navigate",
        description="فتح موقع إلكتروني أو الانتقال لرابط في متصفح الويب الآلي المفتوح أمام المستخدم.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "رابط الموقع الإلكتروني المطلوب فتحه"
                },
                "headless": {
                    "type": "boolean",
                    "description": "تشغيل في الخلفية دون نافذة مرئية (الافتراضي false ليشاهد المستخدم العمل)"
                }
            },
            "required": ["url"]
        },
        handler=tool_browser_navigate,
    )

    # 2. الكتابة في المتصفح
    tool_registry.register_tool(
        name="browser_type",
        description="الكتابة في حقل أو عنصر داخل صفحة المتصفح (مربع بحث، إيميل، كلمة مرور، رسالة).",
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "محدد العنصر CSS أو الـ placeholder مثل 'input[type=search]', 'textarea', '#search'"
                },
                "text": {
                    "type": "string",
                    "description": "النص المراد كتابته"
                },
                "press_enter": {
                    "type": "boolean",
                    "description": "هل يضغط زر Enter بعد الانتهاء من الكتابة؟"
                }
            },
            "required": ["selector", "text"]
        },
        handler=tool_browser_type,
    )

    # 3. النقر على عنصر
    tool_registry.register_tool(
        name="browser_click",
        description="النقر على زر أو رابط أو عنصر داخل صفحة الويب في المتصفح.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "محدد العنصر أو نصه الظاهر مثل 'button.submit', 'text=بحث', 'a#login'"
                }
            },
            "required": ["selector"]
        },
        handler=tool_browser_click,
    )

    # 4. قراءة محتوى الصفحة
    tool_registry.register_tool(
        name="browser_get_page_text",
        description="استخراج وقراءة النصوص والمحتوى المكتوب في صفحة الويب الحالية في المتصفح.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "محدد حاوية معينة اختياري مثل 'article' أو 'main'، أو تركه فارغاً لكامل الصفحة"
                }
            },
        },
        handler=tool_browser_get_page_text,
    )

    # 5. ملء النماذج
    tool_registry.register_tool(
        name="browser_fill_form",
        description="ملء حقول استمارة أو نموذج كامل دفعة واحدة داخل المتصفح.",
        parameters={
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "قاموس الحقول وقيمها مثل {\"input#name\": \"سمير\", \"input#email\": \"samir@ai.com\"}"
                }
            },
            "required": ["fields"]
        },
        handler=tool_browser_fill_form,
    )

    # 6. تنفيذ JavaScript
    tool_registry.register_tool(
        name="browser_execute_script",
        description="تنفيذ كود JavaScript مخصص داخل صفحة الويب المفتوحة في المتصفح وإرجاع النتيجة.",
        parameters={
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "كود الجافاسكربت المراد تنفيذه"
                }
            },
            "required": ["script"]
        },
        handler=tool_browser_execute_script,
    )

    # 7. لقطة شاشة المتصفح
    tool_registry.register_tool(
        name="browser_screenshot",
        description="أخذ لقطة شاشة للصفحة المفتوحة في المتصفح لتحليلها بصرياً ومعاينة ما تم إنجازه.",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=tool_browser_screenshot,
    )

    # 8. إغلاق المتصفح
    tool_registry.register_tool(
        name="browser_close",
        description="إغلاق جلسة المتصفح الآلي بعد الانتهاء من أداء المهام.",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=tool_browser_close,
    )


register_browser_automation_tools()
