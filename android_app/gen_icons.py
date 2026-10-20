"""
يولد أيقونات PNG للتطبيق من صورة JPG المولّدة.
يحتاج: pillow
"""
import sys, os
sys.path.insert(0, r"d:\سمير\core_server\.venv\Lib\site-packages")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ICON_SRC = r"C:\Users\Ziad\.gemini\antigravity-ide\brain\aa3da156-d26d-4899-a91a-e6495f2e326c\samir_app_icon_1789084230530.jpg"
OUT_DIR  = r"d:\سمير\android_app\www\icons"
os.makedirs(OUT_DIR, exist_ok=True)

SIZES = [48, 72, 96, 144, 192, 512]

if HAS_PIL and os.path.exists(ICON_SRC):
    img = Image.open(ICON_SRC).convert("RGBA")
    for s in SIZES:
        resized = img.resize((s, s), Image.LANCZOS)
        resized.save(os.path.join(OUT_DIR, f"icon-{s}.png"))
    print(f"✅ Generated {len(SIZES)} icons in {OUT_DIR}")
else:
    # Fallback: generate solid-color PNG with simple design
    import struct, zlib

    def make_png(size, text="س"):
        """Simple PNG with gradient background"""
        w = h = size
        pixels = []
        for y in range(h):
            row = []
            for x in range(w):
                # Circular mask
                cx, cy = w/2, h/2
                dist = ((x-cx)**2 + (y-cy)**2)**0.5
                radius = min(w,h)/2 - 2
                if dist < radius:
                    # Gradient: dark navy -> cyan tint
                    t = y / h
                    r = int(13 + t * 30)
                    g = int(17 + t * 80)
                    b = int(35 + t * 100)
                    a = 255
                    # Add "S" letter area glow
                    if abs(x - cx) < w*0.3 and abs(y - cy) < h*0.35:
                        r = min(255, r + 40)
                        g = min(255, g + 150)
                        b = min(255, b + 180)
                else:
                    r = g = b = 0; a = 0
                row += [r, g, b, a]
            pixels.append(bytes(row))

        def write_chunk(tag, data):
            crc = zlib.crc32(tag + data) & 0xffffffff
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

        raw = b''.join(b'\x00' + row for row in pixels)
        compressed = zlib.compress(raw, 9)
        png = b'\x89PNG\r\n\x1a\n'
        png += write_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
        png += write_chunk(b'IDAT', compressed)
        png += write_chunk(b'IEND', b'')
        return png

    for s in SIZES:
        png_bytes = make_png(s)
        with open(os.path.join(OUT_DIR, f"icon-{s}.png"), 'wb') as f:
            f.write(png_bytes)
    print(f"✅ Generated fallback icons ({len(SIZES)} sizes) in {OUT_DIR}")

# Also copy 192 and 512 as main references
import shutil
for s in [192, 512]:
    src = os.path.join(OUT_DIR, f"icon-{s}.png")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(OUT_DIR, f"icon-{s}.png"))

print("Done!")
