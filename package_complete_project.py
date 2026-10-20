import os
import sys
import zipfile
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def create_complete_package():
    workspace = Path(__file__).resolve().parent
    zip_path = workspace / "Samir_Project_Complete_Bundle.zip"
    single_doc_path = workspace / "SAMIR_COMPLETE_CODEBASE.md"

    print(f"[*] Packaging complete project from: {workspace}")
    print(f"[*] Target ZIP: {zip_path}")
    print(f"[*] Target Markdown Doc: {single_doc_path}")

    # Paths and folders to ignore
    ignore_dirs = {
        '.venv', 'node_modules', '__pycache__', '.git', '.vscode', '.agents',
        'Samir_Clean_Distribution', 'mario-game', 'android_sdk', 'jdk17', 'projects'
    }
    
    # Extensions to exclude
    ignore_extensions = {
        '.pyc', '.exe', '.ico', '.png', '.jpg', '.jpeg', '.mp3', '.wav', '.zip',
        '.tar', '.gz', '.log', '.tmp', '.class', '.jar', '.aar'
    }

    # Specific files to exclude
    ignore_files = {
        'samir.db', 'samir.db-journal', 'samir.db-wal', 'samir.db-shm',
        'package-lock.json', 'yarn.lock', 'server.log'
    }

    # Collect relevant files
    files_to_bundle = []
    for root, dirs, files in os.walk(workspace):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        rel_root = Path(root).relative_to(workspace)
        if any(part in ignore_dirs for part in rel_root.parts):
            continue

        for f in sorted(files):
            if f in ignore_files:
                continue
            f_path = Path(root) / f
            if f_path.suffix.lower() in ignore_extensions:
                continue
            if f_path == zip_path or f_path == single_doc_path:
                continue
            
            # Don't include other python package scripts
            if f in ["package_complete_project.py"]:
                continue

            rel_file = f_path.relative_to(workspace)
            files_to_bundle.append((f_path, rel_file))

    files_to_bundle.sort(key=lambda x: str(x[1]))
    print(f"[+] Total files selected for bundling: {len(files_to_bundle)}")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. GENERATE CLEAN ZIP ARCHIVE
    # ──────────────────────────────────────────────────────────────────────────
    print(f"[+] Compressing into ZIP: {zip_path.name}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f_path, rel_file in files_to_bundle:
            # If it's a .env file with personal keys, sanitize it
            if rel_file.name == ".env":
                sanitized = (
                    "# Samir AI Configuration\n"
                    "GROQ_API_KEY=\n"
                    "ELEVENLABS_API_KEY=\n"
                    "GEMINI_API_KEY=\n"
                    "OPENAI_API_KEY=\n"
                    "ANTHROPIC_API_KEY=\n"
                    "DEFAULT_AI_PROVIDER=gemini\n"
                    "DEFAULT_TTS_ENGINE=elevenlabs\n"
                )
                zipf.writestr(str(rel_file), sanitized)
            else:
                zipf.write(f_path, str(rel_file))

    zip_size_kb = zip_path.stat().st_size / 1024
    print(f"[✓] ZIP created successfully ({zip_size_kb:.1f} KB)")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. GENERATE ALL-IN-ONE CODEBASE MARKDOWN DOCUMENT
    # ──────────────────────────────────────────────────────────────────────────
    print(f"[+] Compiling All-In-One Codebase document: {single_doc_path.name}...")
    
    def get_code_lang(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        mapping = {
            '.py': 'python',
            '.pyw': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.bat': 'batch',
            '.cmd': 'batch',
            '.sh': 'bash',
            '.md': 'markdown',
            '.txt': 'text',
            '.env': 'ini',
            '.example': 'ini'
        }
        return mapping.get(ext, 'text')

    with open(single_doc_path, 'w', encoding='utf-8') as out:
        out.write("# ⚡ مشروع سمير الذكي (SAMIR AI — J.A.R.V.I.S PROTOCOL)\n")
        out.write("## التوثيق المعماري الكامل وشفرة المصدر الشاملة في ملف واحد\n\n")
        out.write("> هذا الملف يجمع بنية ومشروع سمير الكامل لمشاركته مع نماذج الذكاء الاصطناعي الأخرى (Claude, ChatGPT, Gemini, DeepSeek).\n\n")
        
        out.write("### 📌 نظرة عامة على المشروع (Project Overview):\n")
        out.write("- **الاسم**: سمير (Samir AI Assistant)\n")
        out.write("- **الفلسفة**: رفيق ذكي حقيقي بنظام شبيه بـ J.A.R.V.I.S للتحكم بالحاسوب (Windows)، تشغيل التطبيقات، أتمتة المهام، تحليل الشاشة، الصوت ثنائي الاتجاه، والذاكرة الدائمة.\n")
        out.write("- **الواجهات**: \n")
        out.write("  1. **Core Server**: FastAPI + WebSocket + SQLite + Async Tools (74 أداة نظام مدمجة).\n")
        out.write("  2. **Web Console**: واجهة HUD هولوجرافية مستقبلية (Vanilla JS/CSS/HTML) مع كرة نيون متفاعلة مع الصوت، ودعم كامل للماركداون والقوائم.\n")
        out.write("  3. **Electron App**: تطبيق سطح مكتب إلكترون مدمج بنافذة بدون إطار وقائمة Tray.\n")
        out.write("  4. **Browser Extension**: إضافة متصفح للعمل في الخلفية.\n\n")

        out.write("### 📂 شجرة هيكل المشروع (Project File Tree):\n```text\n")
        for _, rel_file in files_to_bundle:
            out.write(f"{rel_file.as_posix()}\n")
        out.write("```\n\n---\n\n")

        out.write("## 📜 شفرة المصدر لجميع الملفات (Complete Source Code):\n\n")

        for f_path, rel_file in files_to_bundle:
            lang = get_code_lang(rel_file.name)
            out.write(f"### 📄 الملف: `{rel_file.as_posix()}`\n\n")
            out.write(f"```{lang}\n")
            try:
                # Sanitize .env
                if rel_file.name == ".env":
                    content = (
                        "# Samir AI Configuration Template\n"
                        "GROQ_API_KEY=\n"
                        "ELEVENLABS_API_KEY=\n"
                        "GEMINI_API_KEY=\n"
                        "OPENAI_API_KEY=\n"
                        "ANTHROPIC_API_KEY=\n"
                        "DEFAULT_AI_PROVIDER=gemini\n"
                        "DEFAULT_TTS_ENGINE=elevenlabs\n"
                    )
                else:
                    with open(f_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                out.write(content)
            except Exception as e:
                out.write(f"// Error reading file: {e}")
            out.write("\n```\n\n---\n\n")

    doc_size_kb = single_doc_path.stat().st_size / 1024
    print(f"[✓] Complete Codebase Document created successfully ({doc_size_kb:.1f} KB)")
    print("\n[🎉] Done! You now have:")
    print(f"  1. ZIP Archive:  {zip_path}")
    print(f"  2. Full Doc MD:  {single_doc_path}")

if __name__ == "__main__":
    create_complete_package()
