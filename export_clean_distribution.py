import os
import shutil
import sqlite3

def export_clean_package():
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(workspace_root, "Samir_Clean_Distribution")
    
    print(f"[*] Starting clean package export to: {dist_dir}")
    
    # 1. Clean previous export if exists
    if os.path.exists(dist_dir):
        print("[-] Removing previous distribution folder...")
        shutil.rmtree(dist_dir, ignore_errors=True)
    
    os.makedirs(dist_dir, exist_ok=True)
    
    # 2. Copy core_server without temporary files / venvs / personal data
    src_core = os.path.join(workspace_root, "core_server")
    dst_core = os.path.join(dist_dir, "core_server")
    
    def ignore_patterns(folder, files):
        ignored = []
        for f in files:
            if f in [".venv", "__pycache__", ".git", ".pytest_cache", "samir.db", ".env"]:
                ignored.append(f)
            elif f.endswith(".pyc") or f.endswith(".tmp") or f.endswith(".log"):
                ignored.append(f)
        return ignored
    
    print("[+] Copying core_server files...")
    shutil.copytree(src_core, dst_core, ignore=ignore_patterns)
    
    # 3. Create fresh, sanitized samir.db
    dst_data = os.path.join(dst_core, "data")
    os.makedirs(dst_data, exist_ok=True)
    clean_db_path = os.path.join(dst_data, "samir.db")
    
    print("[+] Creating fresh, clean database (zero personal facts, zero chat logs)...")
    conn = sqlite3.connect(clean_db_path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        is_user_approved BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        summary TEXT,
        provider_used TEXT,
        message_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        session_id TEXT,
        sender TEXT NOT NULL,
        content TEXT NOT NULL,
        provider TEXT,
        model TEXT,
        routing_reason TEXT,
        audio_path TEXT,
        tool_calls_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS command_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        tool_name TEXT NOT NULL,
        arguments TEXT,
        status TEXT NOT NULL,
        result TEXT,
        error TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        priority TEXT DEFAULT 'normal',
        category TEXT DEFAULT 'general',
        due_date TIMESTAMP,
        reminder_time TIMESTAMP,
        is_completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS modes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT 0,
        custom_instructions TEXT,
        rules_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS learned_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT,
        mistake_description TEXT,
        correction_rule TEXT NOT NULL,
        tool_involved TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS knowledge_network (
        id TEXT PRIMARY KEY,
        concept TEXT NOT NULL,
        category TEXT DEFAULT 'concept',
        summary TEXT,
        details TEXT,
        importance INTEGER DEFAULT 1,
        references_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Default modes
    INSERT OR IGNORE INTO modes (id, name, description, is_active, custom_instructions)
    VALUES ('default', 'الوضع الطبيعي', 'المساعد الذكي المتكامل للتحكم والأتمتة', 1, '');
    """)
    conn.commit()
    conn.close()
    
    # 4. Create sanitized .env template
    clean_env_path = os.path.join(dst_core, ".env")
    env_content = """# =======================================================
# إعدادات سمير الذكي (Samir AI — J.A.R.V.I.S)
# ضع مفاتيحك الخاصة هنا لتبدأ استخدام سمير بأسلوبك الخاص!
# =======================================================

# 1. مفتاح Groq (موصى به - فائق السرعة ومجاني)
# احصل عليه من: https://console.groq.com/keys
GROQ_API_KEY=

# 2. مفتاح ElevenLabs (للأصوات الطبيعية فائقة الواقعية)
# احصل عليه من: https://elevenlabs.io
ELEVENLABS_API_KEY=

# 3. مفتاح Google Gemini (اختياري للرؤية والبحث)
GEMINI_API_KEY=

# 4. مفتاح OpenAI أو Claude (اختياري)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# الإعدادات الافتراضية الذكية
DEFAULT_AI_PROVIDER=groq
GROQ_CHAT_MODEL=qwen/qwen3.8-27b
DEFAULT_TTS_ENGINE=elevenlabs
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB
"""
    with open(clean_env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    # 5. Create Standalone Launchers
    start_bat_path = os.path.join(dist_dir, "Start_Samir.bat")
    start_bat_content = """@echo off
chcp 65001 >nul
title سمير الذكي — J.A.R.V.I.S AI
color 0B

echo =====================================================================
echo           ⚡ STARK OS // J.A.R.V.I.S PROTOCOL: SAMIR v4.2 ⚡
echo =====================================================================
echo.

cd /d "%~dp0core_server"

:: Check if server already running
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo [OK] سيرفر سمير يعمل بالفعل. جاري فتح التطبيق...
    goto open_app
)

:: Start server
echo [1/2] جاري تشغيل خادم سمير الذكي...
if exist ".venv\\Scripts\\python.exe" (
    start "" /B .venv\\Scripts\\python.exe run_server.py >nul 2>&1
) else (
    start "" /B python run_server.py >nul 2>&1
)

:: Wait for ready
set /a attempts=0
:wait_loop
timeout /t 1 /nobreak >nul
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% equ 0 goto open_app

set /a attempts+=1
if %attempts% geq 8 goto open_app
goto wait_loop

:open_app
echo [2/2] فتح واجهة سمير بنمط التطبيق المكتبي المستقل...
start "" msedge.exe --app=http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 goto done

start "" chrome.exe --app=http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 goto done

start http://localhost:8000/

:done
echo [OK] تم تشغيل سمير بنجاح!
timeout /t 2 >nul
exit
"""
    with open(start_bat_path, "w", encoding="utf-8") as f:
        f.write(start_bat_content)

    # 6. Create 1-Install_Requirements.bat
    install_bat_path = os.path.join(dist_dir, "Install_Dependencies.bat")
    install_bat_content = """@echo off
chcp 65001 >nul
title تثبيت متطلبات سمير الذكي
color 0A

echo =====================================================================
echo           تثبيت متطلبات ومكتبات سمير الذكي (Samir AI)
echo =====================================================================
echo.

cd /d "%~dp0core_server"

echo [1/3] التحقق من بايثون...
python --version
if %errorlevel% neq 0 (
    echo [خطأ] بايثون غير مثبت على هذا الجهاز! يرجى تثبيت Python 3.10 أو أحدث.
    pause
    exit /b 1
)

echo [2/3] إنشاء البيئة الافتراضية (.venv)...
if not exist ".venv" (
    python -m venv .venv
)

echo [3/3] تثبيت الحزم والمكتبات...
.\\.venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\.venv\\Scripts\\pip.exe install -r requirements.txt

echo.
echo [✓] تم تثبيت كافة المتطلبات بنجاح!
echo الآن يمكنك فتح ملف Start_Samir.bat واستخدام سمير مباشرة.
pause
"""
    with open(install_bat_path, "w", encoding="utf-8") as f:
        f.write(install_bat_content)

    # 7. Create Readme file
    readme_path = os.path.join(dist_dir, "README_دليل_التشغيل.txt")
    readme_content = """=====================================================================
         ⚡ سمير الذكي — المساعد الشخصي الخارق (J.A.R.V.I.S AI) ⚡
=====================================================================

أهلاً بك في النسخة النظيفة الجاهزة للمشاركة من مشروع "سمير الذكي".
هذه النسخة خالية تماماً من أي بيانات شخصية أو ذكريات أو مفاتيح سابقة.

طريقة التشغيل لأي مستخدم جديد:
----------------------------------
1. افتح ملف Install_Dependencies.bat (مرة واحدة فقط لتثبيت المكتبات).
2. افتح ملف core_server/.env وضع فيه مفاتيح الذكاء الاصطناعي الخاصة بك (مثل Groq أو ElevenLabs).
3. اضغط مرتين على Start_Samir.bat وسيفتح البرنامج فوراً في نافذة مستقلة أنيقة.

المميزات المتوفرة:
----------------------------------
- واجهة هولوغرافية تشبه J.A.R.V.I.S مع مفاعل الآرك وواجهة أوامر تفاعلية.
- إمكانية الكتابة والتحدث الصوتي بالمايك مع الكشف التلقائي للصمت (VAD 1.5s).
- أرشيف وسجل محادثات كامل وقابل للبحث والاسترجاع.
- أتمتة كاملة للكمبيوتر: فتح البرامج، فوتوشوب، بريمير، كامتاسيا، الرسام.
- كتابة وتشغيل الأكواد والملفات على الجهاز.
- بناء مواقع كاملة وألعاب واستضافتها محلياً بنقرة زر.

مع تحيات سمير الذكي!
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n[✓] Export completed successfully to: {dist_dir}")

if __name__ == '__main__':
    export_clean_package()
