import asyncio
import edge_tts

voices = [
    "ar-SA-HamedNeural",
    "ar-SA-ZariyahNeural",
    "ar-EG-ShakirNeural",
    "ar-EG-SalmaNeural",
    "ar-AE-HamdanNeural",
    "ar-LB-RamiNeural",
    "ar-JO-TaimNeural"
]

async def test_voices():
    for v in voices:
        try:
            comm = edge_tts.Communicate("مرحباً بك يا صديقي، أنا سمير.", voice=v)
            audio = b""
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
            print(f"Voice {v}: SUCCESS ({len(audio)} bytes)")
        except Exception as e:
            print(f"Voice {v}: FAILED ({e})")

asyncio.run(test_voices())
