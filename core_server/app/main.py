import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_database
from app.api.routes_chat import router as chat_router
from app.api.routes_memory import router as memory_router
from app.api.routes_devices import router as devices_router
from app.api.routes_logs import router as logs_router
from app.api.routes_tasks import router as tasks_router
from app.api.routes_providers import router as providers_router
from app.api.websocket_hub import router as ws_router
from app.api.routes_projects import router as projects_router
from app.api.routes_conversations import router as conversations_router
from app.api.routes_auth import router as auth_router
from app.api.routes_custom_rules import router as custom_rules_router

# تحميل جميع الأدوات عند بدء التشغيل
import app.tools.default_tools          # الأدوات الأساسية: الوقت، الذاكرة، النظام
import app.tools.web_search_tool        # البحث في الإنترنت
import app.tools.task_tool              # إدارة المهام والتذكيرات
import app.tools.modes_tool             # أوضاع العمل: Creator، Gaming، Work، Night
import app.tools.image_generation_tool  # توليد ورسم الصور بالذكاء الاصطناعي
import app.tools.code_runner_tool       # كتابة وتنفيذ الأكواد البرمجية
import app.tools.browser_media_tool     # فتح التابات والبحث المباشر في يوتيوب
import app.tools.learning_tool          # التعلم الذاتي العميق والدروس
import app.tools.windows_agent_tool     # التحكم بويندوز، لقطات الشاشة والماوس والكيبورد
import app.tools.antigravity_bridge_tool # جسر الربط وقراءة مهارات وقدرات أنتي قرافيتي
import app.tools.web_builder_tool       # محرك إبداع سمير لبناء المواقع والألعاب
import app.tools.game_launcher_tool      # إطلاق وتشغيل الألعاب التفاعلية فوراً على الشاشة
import app.tools.browser_automation_tool # أتمتة المتصفح والكتابة والنقر عبر Playwright
import app.tools.notifications_tool      # تنبيهات ويندوز الذكية وجدولة التذكيرات
import app.tools.clipboard_tool          # قراءة ونسخ محتوى الحافظة
import app.tools.gmail_tool              # إرسال وقراءة وبحث الإيميلات عبر Gmail
import app.tools.calendar_tool          # إدارة المواعيد والجداول عبر Google Calendar
import app.tools.business_metrics_tool  # Stripe + Analytics + Instagram — التقرير الصباحي
import app.tools.terminal_tool           # تشغيل أوامر Terminal / PowerShell / Python بأمان
import app.tools.link_inspector_tool     # فحص ودخول روابط إنستغرام ويوتيوب والويب

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("samir.main")

WEB_CONSOLE_DIR = Path(__file__).resolve().parent.parent / "web_console"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  SAMIR AI Assistant — Core Hub Starting...")
    logger.info("=" * 60)
    await init_database()
    logger.info("Database initialized.")
    logger.info("All tools loaded and registered.")

    # تشغيل نفق الاتصال السحابي للهاتف الذكي
    try:
        from app.core.tunnel_service import tunnel_service
        await tunnel_service.start()
    except Exception as e:
        logger.warning(f"Could not start tunnel service: {e}")

    yield
    logger.info("SAMIR Core Hub stopped.")


app = FastAPI(
    title="Samir AI Assistant Core Hub",
    description="النواة المركزية لمساعد سمير الذكي — الصوت، الذاكرة، الأدوات، الأجهزة",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS — يسمح بالاتصال من المتصفح مباشرة ومن ملفات local file://
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(custom_rules_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(auth_router)
app.include_router(ws_router)

# Web Console & Uploads
from app.media.file_processor import UPLOADS_DIR

if WEB_CONSOLE_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_CONSOLE_DIR)), name="static")

if UPLOADS_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# استضافة مشاريع الويب والألعاب
PROJECTS_DIR = Path("./projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/projects", StaticFiles(directory=str(PROJECTS_DIR), html=True), name="projects")

SANDBOX_DIR = Path("./data/sandbox")
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media/sandbox", StaticFiles(directory=str(SANDBOX_DIR), html=True), name="sandbox")

from pydantic import BaseModel, Field

class CodeExecutionPayload(BaseModel):
    language: str = Field(default="python", description="Language: python, javascript, powershell, html")
    code: str = Field(..., description="Source code to execute")
    timeout_seconds: int = Field(default=15, description="Timeout in seconds")

@app.post("/api/v1/code/execute")
async def execute_code_api(payload: CodeExecutionPayload):
    """تنفيذ كود برمجي فورياً للواجهة وتشغيل الألعاب أو إرجاع مخرجات الكونسول"""
    from app.tools.code_runner_tool import tool_execute_code
    res = await tool_execute_code(payload.language, payload.code, payload.timeout_seconds)
    return res




@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav = WEB_CONSOLE_DIR / "favicon.ico"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/x-icon")
    return FileResponse(str(WEB_CONSOLE_DIR / "samir-logo.png"), media_type="image/png")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "assistant": "Samir (سمير)",
        "version": "1.1.0",
        "mode": "cloud_24_7"
    }


@app.get("/")
async def root():
    index_file = WEB_CONSOLE_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "assistant": "Samir (سمير)",
        "status": "online",
        "version": "1.1.0",
        "docs": "/docs",
    }



@app.get("/style.css", include_in_schema=False)
async def get_style_css():
    css_file = WEB_CONSOLE_DIR / "style.css"
    if css_file.exists():
        return FileResponse(str(css_file), media_type="text/css")
    return FileResponse(str(WEB_CONSOLE_DIR / "index.html"))


@app.get("/manifest.json", include_in_schema=False)
async def get_manifest_json():
    m_file = WEB_CONSOLE_DIR / "manifest.json"
    if m_file.exists():
        return FileResponse(str(m_file), media_type="application/manifest+json")
    return {}


@app.get("/sw.js", include_in_schema=False)
async def get_sw_js():
    sw_file = WEB_CONSOLE_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript")
    return ""


@app.get("/api/v1/network/info")
async def get_network_info():
    """معلومات عنوان الشبكة المحلية والنفق السحابي الآمن للاتصال بالهاتف وعرض الباركود QR"""
    import socket
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    port = settings.PORT
    lan_url = f"http://{local_ip}:{port}"

    # جلب رابط Cloudflare Tunnel (HTTPS) الآمن إن وُجد
    tunnel_url = None
    try:
        from app.core.tunnel_service import tunnel_service
        tunnel_url = tunnel_service.get_url()
    except Exception:
        pass

    # أفضل رابط يعمل للهواتف فورياً بدون أي حجب للشبكة مع تفعيل الميكروفون
    best_mobile_url = tunnel_url or lan_url
    
    qr_b64 = ""
    try:
        import qrcode
        import io
        import base64
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(best_mobile_url)
        qr.make(fit=True)
        # أسود نقي على خلفية بيضاء نقية لضمان قراءة وفحص كاميرات جميع الهواتف (آيفون وأندرويد) فورياً وبأعلى دقة
        img = qr.make_image(fill_color="#000000", back_color="#ffffff")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to generate QR: {e}")

    return {
        "status": "success",
        "local_ip": local_ip,
        "port": port,
        "mobile_url": best_mobile_url,
        "lan_url": lan_url,
        "tunnel_url": tunnel_url,
        "qr_base64": qr_b64,
        "is_https": best_mobile_url.startswith("https://"),
    }


@app.get("/api/v1/knowledge")
async def get_knowledge(limit: int = 50):
    import aiosqlite
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, topic, summary, created_at FROM samir_knowledge ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return {"items": [dict(r) for r in rows]}


@app.get("/api/v1/gallery")
async def get_gallery():
    gen_dir = WEB_CONSOLE_DIR / "generated"
    images = []
    if gen_dir.exists():
        all_files = list(gen_dir.glob("*.png")) + list(gen_dir.glob("*.jpg")) + list(gen_dir.glob("*.jpeg")) + list(gen_dir.glob("*.webp"))
        all_files.sort(key=os.path.getmtime, reverse=True)
        for f in all_files:
            images.append({
                "filename": f.name,
                "url": f"/static/generated/{f.name}",
                "timestamp": int(f.stat().st_mtime),
            })
    return {"images": images[:60]}


@app.get("/health")
async def health():
    from app.tools.base_tool import tool_registry
    return {
        "status": "healthy",
        "assistant": "Samir",
        "version": "1.2.0",
        "tools_registered": len(tool_registry.get_all_tool_schemas()),
        "ready": True,
    }
