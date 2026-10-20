import httpx

voices_to_test = [
    ("ar-SA-HamedNeural", "حامد السعودي"),
    ("ar-SA-ZariyahNeural", "زارية السعودية"),
    ("ar-EG-ShakirNeural", "شاكر المصري"),
    ("ar-AE-HamdanNeural", "حمدان الإماراتي"),
    ("ar-LB-RamiNeural", "رامي اللبناني"),
    ("pNInz6obpgDQGcFmaJgB", "آدم (ElevenLabs / Fallback)"),
    ("EXAVITQu4vr4xnSDxMaL", "سارة (ElevenLabs / Fallback)")
]

for vid, label in voices_to_test:
    r = httpx.post("http://localhost:8000/api/v1/chat/tts", data={"text": "أهلاً بك، هذا فحص صوت سمير.", "voice": vid})
    print(f"Voice ID {vid[:20]}: status={r.status_code}, bytes={len(r.content)}")
