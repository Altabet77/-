import os
import io
import time
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image

logger = logging.getLogger("samir.media.processor")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
MODIFIED_DIR = UPLOADS_DIR / "modified"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MODIFIED_DIR.mkdir(parents=True, exist_ok=True)


class FileProcessor:
    @staticmethod
    async def process_uploaded_file(file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """معالجة وحفظ الملف المرفوع واستخراج معلوماته ومحتواه للنموذج"""
        safe_name = f"{int(time.time())}_{filename.replace(' ', '_')}"
        save_path = UPLOADS_DIR / safe_name
        
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        file_ext = Path(filename).suffix.lower()
        size_bytes = len(file_bytes)
        size_kb = round(size_bytes / 1024, 2)
        public_url = f"/uploads/{safe_name}"

        info: Dict[str, Any] = {
            "original_filename": filename,
            "stored_filename": safe_name,
            "local_path": str(save_path),
            "url": public_url,
            "size_kb": size_kb,
            "extension": file_ext,
            "category": "unknown",
            "extracted_text": "",
            "summary": "",
            "is_image": False,
            "is_video": False,
            "is_document": False,
            "is_code": False,
        }

        # 1. Images
        if file_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
            info["category"] = "image"
            info["is_image"] = True
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
            info["mime_type"] = mime_map.get(file_ext, "image/jpeg")
            try:
                from PIL import ImageStat
                with Image.open(io.BytesIO(file_bytes)) as img:
                    width, height = img.size
                    img_format = img.format or file_ext.replace(".", "").upper()
                    aspect_ratio = round(width / height, 2) if height > 0 else 1.0
                    info["dimensions"] = f"{width}x{height}"
                    info["aspect_ratio"] = aspect_ratio
                    info["format"] = img_format
                    
                    # Local lighting and color analysis
                    stat = ImageStat.Stat(img.convert("RGB"))
                    r, g, b = stat.mean[:3]
                    brightness = (r * 299 + g * 587 + b * 114) / 1000
                    tone = "إضاءة نهارية/فاتحة" if brightness > 150 else ("إضاءة معتدلة" if brightness > 80 else "إضاءة ليلية/داكنة")
                    
                    color_desc = []
                    if r > 150 and g < 110 and b < 110:
                        color_desc.append("طابع لوني أحمر بارز")
                    elif g > 150 and r < 110 and b < 110:
                        color_desc.append("طابع لوني أخضر بارز")
                    elif b > 150 and r < 120 and g < 140:
                        color_desc.append("طابع لوني أزرق/سماوي")
                    elif r > 180 and g > 180 and b < 120:
                        color_desc.append("ألوان دافئة (أصفر/برتقالي)")
                    elif r > 200 and g > 200 and b > 200:
                        color_desc.append("ألوان بيضاء/فاتحة ناصعة")
                    elif r < 60 and g < 60 and b < 60:
                        color_desc.append("ألوان داكنة/سوداء")
                    else:
                        color_desc.append(f"ألوان متوازنة (RGB: {int(r)}, {int(g)}, {int(b)})")

                    colors_str = "، ".join(color_desc)
                    info["tone"] = tone
                    info["dominant_colors"] = colors_str
                    info["summary"] = f"صورة بصيغة {img_format} بأبعاد {width}×{height} بكسل (نسبة العرض للارتفاع {aspect_ratio})، بحجم {size_kb} KB. الإضاءة: {tone}، السمة اللونية: {colors_str}."
            except Exception as e:
                logger.warning(f"Error parsing image {filename}: {e}")
                info["summary"] = f"صورة مرفوعة بحجم {size_kb} KB."
            
            # Base64 data for Multimodal Vision Models
            if size_bytes < 15 * 1024 * 1024:
                info["base64"] = base64.b64encode(file_bytes).decode("utf-8")

        # 2. Documents & PDFs
        elif file_ext == ".pdf":
            info["category"] = "document"
            info["is_document"] = True
            info["mime_type"] = "application/pdf"
            if size_bytes < 15 * 1024 * 1024:
                info["base64"] = base64.b64encode(file_bytes).decode("utf-8")
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                num_pages = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages[:20]):  # First 20 pages max
                    txt = page.extract_text() or ""
                    if txt.strip():
                        pages_text.append(f"--- صفحة {idx + 1} ---\n{txt.strip()}")
                
                extracted = "\n\n".join(pages_text)
                info["extracted_text"] = extracted[:30000]
                info["pages_count"] = num_pages
                info["summary"] = f"ملف PDF يحتوي على {num_pages} صفحات، تم استخراج محتواه بنجاح ({len(extracted)} حرف)."
            except Exception as e:
                logger.warning(f"Error extracting PDF text: {e}")
                info["summary"] = f"ملف PDF بحجم {size_kb} KB (تعذر استخراج النص المباشر: {e})."

        # 3. Source Code & Text files
        elif file_ext in [
            ".txt", ".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".csv",
            ".sql", ".sh", ".ps1", ".bat", ".xml", ".yaml", ".yml", ".c", ".cpp",
            ".cs", ".java", ".php", ".rs", ".go"
        ]:
            info["category"] = "code" if file_ext != ".txt" else "text"
            info["is_code"] = (file_ext != ".txt")
            info["is_document"] = True
            info["mime_type"] = "text/plain"
            try:
                # Detect UTF-8 or fallback to latin-1
                try:
                    text_content = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = file_bytes.decode("cp1256", errors="replace")
                
                info["extracted_text"] = text_content[:40000]
                lines_count = len(text_content.splitlines())
                info["lines_count"] = lines_count
                info["summary"] = f"ملف برمجي/نصي ({file_ext}) يحتوي على {lines_count} سطر بحجم {size_kb} KB."
            except Exception as e:
                info["summary"] = f"ملف نصي بحجم {size_kb} KB."

        # 4. Videos
        elif file_ext in [".mp4", ".webm", ".mov", ".avi", ".mkv"]:
            info["category"] = "video"
            info["is_video"] = True
            info["mime_type"] = "video/webm" if file_ext == ".webm" else "video/mp4"
            if size_bytes < 20 * 1024 * 1024:
                info["base64"] = base64.b64encode(file_bytes).decode("utf-8")
            info["summary"] = f"مقطع فيديو ({file_ext}) بحجم {size_kb} KB، متاح للعرض والتحليل داخل سمير."

        # 5. Audio
        elif file_ext in [".mp3", ".wav", ".m4a", ".ogg"]:
            info["category"] = "audio"
            info["mime_type"] = "audio/mpeg" if file_ext == ".mp3" else "audio/wav"
            if size_bytes < 15 * 1024 * 1024:
                info["base64"] = base64.b64encode(file_bytes).decode("utf-8")
            info["summary"] = f"ملف صوتي ({file_ext}) بحجم {size_kb} KB."

        else:
            info["category"] = "file"
            info["summary"] = f"ملف مرفق ({file_ext}) بحجم {size_kb} KB."

        return info

    @staticmethod
    def save_modified_file(original_filename: str, new_content: str) -> Dict[str, Any]:
        """حفظ ملف تم تعديله بواسطة سمير وتوفير رابط تنزيل مباشر"""
        base_stem = Path(original_filename).stem
        ext = Path(original_filename).suffix or ".txt"
        modified_filename = f"{base_stem}_modified_{int(time.time())}{ext}"
        mod_path = MODIFIED_DIR / modified_filename
        
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return {
            "status": "success",
            "filename": modified_filename,
            "url": f"/uploads/modified/{modified_filename}",
            "local_path": str(mod_path),
            "size_chars": len(new_content),
            "lines": len(new_content.splitlines()),
        }


file_processor = FileProcessor()
