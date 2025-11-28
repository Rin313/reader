import translators as ts

def translate_text_wrapper(
    text: str, 
    translator: str = 'bing', 
    from_lang: str = 'auto', 
    to_lang: str = 'cn'
) -> str:
    if not text:
        return ""
    try:
        result = ts.translate_text(
            query_text=text,
            translator=translator,
            from_language=from_lang,
            to_language=to_lang
        )
        return result
    except Exception as e:
        print(f"Translation failed: {str(e)}")
        raise e