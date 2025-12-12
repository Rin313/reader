import os
os.environ["translators_default_region"] = "EN"
import translators as ts
import deepl
import random

# 从环境变量获取 DeepL API key
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")

# 不要使用并发
def translate_text_wrapper(
    text: str, 
    translator: str, 
    to_lang: str,
    from_lang: str = 'auto'
) -> str:
    if not text:
        return ""
    # 如果是 deepl，使用官方 API
    if translator.lower() == 'deepl':
        try:
            deepl_client = deepl.DeepLClient(DEEPL_API_KEY)
            
            # 构建参数
            kwargs = {'target_lang': to_lang}
            
            # 如果指定了源语言且不是 auto，则添加 source_lang 参数
            if from_lang and from_lang.lower() != 'auto':
                kwargs['source_lang'] = from_lang
            
            result = deepl_client.translate_text(text, **kwargs)
            return result.text
        except Exception as e:
            print(f"DeepL translation failed: {str(e)}")
            raise e
    
    # 其他翻译引擎使用 translators 库
    kwargs = {
        'query_text': text,
        'translator': translator,
        'from_language': from_lang,
        'to_language': to_lang,
        'http_client': 'httpx',
        'sleep_seconds': random.uniform(0.2, 0.6),
    }
    try:
        result = ts.translate_text(**kwargs)
        return result
    except Exception as e:
        print(f"Translation failed: {str(e)}")
        raise e