import httpx

r = httpx.post("http://localhost:8000/api/v1/chat/voice/select", json={"voice_or_dialect": "ar-SA-ZariyahNeural"})
print("Select response:", r.status_code, r.text)
