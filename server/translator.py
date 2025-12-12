import os
os.environ["translators_default_region"] = "EN"
import translators as ts
import random

# 不要使用并发
def translate_text_wrapper(
    text: str, 
    translator: str, 
    to_lang: str,
    from_lang: str = 'auto'
) -> str:
    if not text:
        return ""
    kwargs = {
        'query_text': text,
        'translator': translator,
        'from_language': from_lang,
        'to_language': to_lang,
        # --- 优化项 ---
        'http_client': 'httpx',         # 尝试更快的客户端
        'sleep_seconds': random.uniform(0.2, 0.6), # 随机休眠防封
    }
    try:
        result = ts.translate_text(**kwargs)
        return result
    except Exception as e:
        print(f"Translation failed: {str(e)}")
        raise e