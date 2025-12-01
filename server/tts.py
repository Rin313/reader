import edge_tts
from typing import AsyncGenerator

async def generate_audio_stream(
    text: str, 
    voice: str, 
    rate: str = "+0%"
) -> AsyncGenerator[bytes, None]:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate
    )
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]