import os
os.environ["translators_default_region"] = "EN"
import translators as ts
import deepl
import random
from common import get_app_path

def load_deepl_key(filename="deepl_key.txt"):
    """
    读取并返回 API Key，如果文件不存在则创建并提示退出
    """
    # 组合完整路径：程序根目录 + 文件名
    config_path = os.path.join(get_app_path(), filename)
    # 检查文件是否存在
    if not os.path.exists(config_path):
        try:
            # 创建一个空文件，方便用户直接打开填写
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write("") 
            print(f"已自动创建配置文件：{config_path}")
            print("请打开配置文件，粘贴 DeepL API Key 并保存，然后重新运行本程序。")
        except Exception as e:
            print(f"【错误】无法创建配置文件: {e}")

    # 读取文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            # .strip() 去除首尾的空格、换行符，防止用户复制出错
            api_key = f.read().strip()
    except Exception as e:
        print(f"【错误】读取配置文件失败: {e}")
    # 检查 Key 是否为空
    # if not api_key:
    #     print(f"【提示】配置文件 '{filename}' 是空的。")
    return api_key
# 从环境变量获取 DeepL API key
DEEPL_API_KEY = load_deepl_key()

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