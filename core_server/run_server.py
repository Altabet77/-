import sys
import uvicorn

from pathlib import Path

# Redirect stdout/stderr to log file if running under pythonw (where stdout is None)
if sys.stdout is None or sys.stderr is None:
    log_dir = Path(__file__).resolve().parent / "data"
    log_dir.mkdir(exist_ok=True)
    log_file = open(log_dir / "server.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file

# Fix Windows console encoding for Arabic / emoji output
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.core.config import settings

if __name__ == "__main__":
    import time

    print(f">> Starting Samir AI Assistant Core Hub on http://localhost:{settings.PORT}")
    print(f">> Web Voice Console: http://localhost:{settings.PORT}/")
    print(f">> WebSocket voice:   ws://localhost:{settings.PORT}/ws/voice")

    while True:
        try:
            uvicorn.run(
                "app.main:app",
                host=settings.HOST,
                port=settings.PORT,
                reload=False
            )
            # Normal shutdown (Ctrl+C / SIGINT / SIGTERM)
            break
        except KeyboardInterrupt:
            print("\n>> Samir server stopped by user.")
            break
        except Exception as e:
            print(f">> [Samir 24/7 Resilience] Server crashed with error: {e}. Auto-restarting in 3 seconds...")
            time.sleep(3)
