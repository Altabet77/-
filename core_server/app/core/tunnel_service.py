import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("samir.tunnel")

class TunnelService:
    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.public_url: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._url_file = Path("d:/سمير/tunnel_url.txt")

    def get_url(self) -> Optional[str]:
        if self.public_url:
            return self.public_url
        if self._url_file.exists():
            try:
                content = self._url_file.read_text(encoding="utf-8").strip()
                if content.startswith("https://") and "trycloudflare.com" in content:
                    self.public_url = content
                    return content
            except Exception:
                pass
        return None

    async def start(self):
        """بدء تشغيل Cloudflare Tunnel للحصول على رابط HTTPS مباشر للهاتف مجاناً وبدون تثبيت"""
        cloudflared_path = Path("d:/سمير/cloudflared.exe")
        if not cloudflared_path.exists():
            logger.info("cloudflared.exe not found at d:/سمير/cloudflared.exe")
            return

        # فحص إذا كان هناك رابط مخزن ومتاح
        current = self.get_url()
        if current:
            logger.info(f"Existing Tunnel URL found: {current}")

        self._task = asyncio.create_task(self._run_tunnel(cloudflared_path))

    async def _run_tunnel(self, exe_path: Path):
        url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        while True:
            try:
                cmd = [str(exe_path), "tunnel", "--url", "http://localhost:8000"]
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logger.info("Cloudflare tunnel started.")

                async def read_stream(stream):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        text = line.decode("utf-8", errors="ignore")
                        match = url_pattern.search(text)
                        if match:
                            url = match.group(0)
                            self.public_url = url
                            try:
                                self._url_file.write_text(url, encoding="utf-8")
                            except Exception:
                                pass
                            logger.info(f"⚡ Live Cloudflare Tunnel URL ready: {url}")

                await asyncio.gather(
                    read_stream(self.process.stdout),
                    read_stream(self.process.stderr)
                )
            except Exception as e:
                logger.warning(f"Error in Cloudflare tunnel: {e}")
            
            logger.info("Cloudflare tunnel exited. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

tunnel_service = TunnelService()
