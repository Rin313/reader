"""
epub是一个zip包：
- mimetype：声明文档格式
- container.xml：声明配置文件路径
- .opf：配置文件，包含Metadata、Manifest（声明引用的HTML、图片、CSS、字体等）、Spine（定义线性阅读顺序）、Guide（过时的）
- nav.xhtml：导航文档，用于生成目录树
- toc.ncx：过时的导航文档格式
- Content Documents & Assets：包含图片、字体、css、视频、音频，以及XHTML/HTML5
"""
import ebooklib
from ebooklib import epub

from bs4 import BeautifulSoup, Comment
import re
from typing import List, Optional, Set
from dataclasses import dataclass

def extract_epub(file_path: str) -> List[str]:
    try:
        book = epub.read_epub(file_path)
        paragraphs = []
        # processed_ids = set()
        # 1. 先按 spine 顺序处理主要内容
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item is not None:
                content = item.get_content()
                paragraphs.extend(clean_html_advanced(content))
                # processed_ids.add(item_id)
        # 2. 可选：处理不在 spine 中的其他文档
        # for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        #     if item.get_id() not in processed_ids:
        #         content = item.get_content()
        #         paragraphs.extend(clean_html_advanced(content))
        return paragraphs
    except Exception as e:
        print(f"Error parsing EPUB: {str(e)}")
        return []
@dataclass
class CleanConfig:
    """清洗配置"""
    # 要删除的标签
    remove_tags: Set[str] = None
    # 要提取的内容标签
    content_tags: Set[str] = None
    # 最小文本长度
    min_length: int = 2
    # 是否规范化空白
    normalize_whitespace: bool = True
    # 是否移除图片的alt文本
    keep_img_alt: bool = True
    # 是否合并连续文本
    merge_consecutive: bool = False
    
    def __post_init__(self):
        if self.remove_tags is None:
            self.remove_tags = {
                'script', 'style', 'meta', 'link', 'head',
                'nav', 'header', 'footer', 'aside', 'noscript',
                'iframe', 'form', 'button', 'input', 'svg',
                'canvas', 'audio', 'video', 'source', 'embed',
                'object', 'applet', 'map', 'area'
            }
        if self.content_tags is None:
            self.content_tags = {
                'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'li', 'blockquote', 'pre', 'td', 'th',
                'caption', 'figcaption', 'dt', 'dd'
            }


def clean_html_advanced(
    html_content: str, 
    config: Optional[CleanConfig] = None
) -> List[str]:
    """
    高级 HTML 清洗函数
    
    Args:
        html_content: HTML 字符串
        config: 清洗配置
        
    Returns:
        清洗后的文本列表
    """
    if config is None:
        config = CleanConfig()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 保存图片 alt 文本（如果需要）
    img_alts = []
    if config.keep_img_alt:
        for img in soup.find_all('img', alt=True):
            if img['alt'].strip():
                img_alts.append(f"[图片: {img['alt'].strip()}]")
    
    # 2. 删除噪音标签
    for tag in config.remove_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    # 3. 删除 HTML 注释
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        comment.extract()
    
    # 4. 删除特定 class 的噪音元素
    noise_classes = ['footnote', 'sidebar', 'advertisement', 'ad', 'banner']
    for cls in noise_classes:
        for element in soup.find_all(class_=re.compile(cls, re.I)):
            element.decompose()
    
    # 5. 删除隐藏元素
    for element in soup.find_all(style=re.compile(r'display\s*:\s*none', re.I)):
        element.decompose()
    for element in soup.find_all(attrs={'hidden': True}):
        element.decompose()
    
    # 6. 删除所有标签的属性（清理HTML）
    for tag in soup.find_all(True):
        tag.attrs = {}
    
    # 7. 提取文本
    result = []
    seen = set()  # 用于去重
    
    body = soup.find('body') or soup
    
    for element in body.find_all(config.content_tags):
        # 避免嵌套元素重复提取
        if any(parent.name in config.content_tags 
               for parent in element.parents if parent.name):
            continue
        
        text = element.get_text(separator=' ', strip=True)
        
        if config.normalize_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()
        
        # 过滤条件
        if not text or len(text) < config.min_length:
            continue
        
        # 去重
        if text in seen:
            continue
        seen.add(text)
        
        result.append(text)
    
    # 8. 添加图片描述（如果有）
    result.extend(img_alts)
    
    # 9. 合并连续短文本（可选）
    if config.merge_consecutive:
        result = merge_short_texts(result, threshold=50)
    
    return result


def merge_short_texts(texts: List[str], threshold: int = 50) -> List[str]:
    """合并连续的短文本"""
    if not texts:
        return texts
    
    merged = []
    buffer = []
    
    for text in texts:
        if len(text) < threshold:
            buffer.append(text)
        else:
            if buffer:
                merged.append(' '.join(buffer))
                buffer = []
            merged.append(text)
    
    if buffer:
        merged.append(' '.join(buffer))
    
    return merged