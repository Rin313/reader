import edge_tts
from typing import AsyncGenerator, List, Dict

async def get_all_voices() -> List[Dict]:
    try:
        voices = await edge_tts.list_voices()
        # 简单筛选一下关键信息返回
        return [
            {
                "ShortName": v["ShortName"],
                "Gender": v["Gender"],
                "Locale": v["Locale"]
            }
            for v in voices
        ]
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return []

async def generate_audio_stream(
    text: str, 
    voice: str = "zh-CN-XiaoxiaoNeural", 
    rate: str = "+0%"
) -> AsyncGenerator[bytes, None]:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate
    )
    # 使用 stream() 方法获取数据块
    async for chunk in communicate.stream():
        # edge-tts 的 stream 会返回多种类型的 chunk (audio, WordBoundary 等)，我们只需要音频数据
        if chunk["type"] == "audio":
            yield chunk["data"]