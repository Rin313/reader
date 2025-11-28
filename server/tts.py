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
        # edge-tts 的 stream 会返回多种类型的 chunk (audio, WordBoundary 等)，我们只需要音频数据
        if chunk["type"] == "audio":
            yield chunk["data"]