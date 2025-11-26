import translators as ts

def translate_text_wrapper(
    text: str, 
    translator: str = 'bing', 
    from_lang: str = 'auto', 
    to_lang: str = 'en'
) -> str:
    """
    包装 translators.translate_text 函数
    
    :param text: 需要翻译的文本
    :param translator: 翻译引擎 (alibaba, bing, google, baidu, etc.)
    :param from_lang: 源语言
    :param to_lang: 目标语言
    :return: 翻译后的文本
    """
    if not text:
        return ""
        
    try:
        # 调用库函数
        result = ts.translate_text(
            query_text=text,
            translator=translator,
            from_language=from_lang,
            to_language=to_lang
        )
        return result
    except Exception as e:
        # 捕获潜在的网络错误或API限制错误，并向上抛出以便API层处理
        print(f"Translation failed: {str(e)}")
        raise e