import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import trafilatura
import mobi
import os
import shutil
import re
from typing import List
# 必须保证每个段落不以换行符结尾，才能实现翻译批处理精度足够。

def is_sentence_end(text: str) -> bool:
    """
    判断文本是否以句子结束符结尾。
    涵盖中文标点和英文标点。
    """
    if not text:
        return True
    # 常见的句子结束符
    endings = ('.', '!', '?', '。', '！', '？', '…', '"', '”', "'", '’')
    return text.rstrip().endswith(endings)

def is_cjk(char):
    """检查字符是否为 CJK (中日韩) 字符"""
    if not char: 
        return False
    return '\u4e00' <= char <= '\u9fff'

def post_process_text_list(paragraphs: List[str]) -> List[str]:
    """
    对提取出的初步段落列表进行二次清洗和合并。
    解决：上一段没结束就换行的问题（PDF/TXT常见问题）。
    """
    merged_paragraphs = []
    buffer = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 逻辑 A: 处理 buffer 结尾的连字符 (Hyphenation) - 主要针对英文 PDF
        if buffer and buffer.endswith('-') and not buffer.endswith('--'):
            # 获取 buffer 的最后一个词（去除 -）和 para 的第一个词
            # 简单的启发式策略：
            # 1. 如果 para 首字母是小写 (ex: "inf-", "ormation") -> 合并为 "information"
            # 2. 如果 para 首字母是大写 (ex: "pre-", "Covid") -> 可能是 "pre-Covid"，保留连字符
            if para and para[0].islower():
                buffer = buffer[:-1] + para
            else:
                # 保留连字符，直接拼接
                buffer += para
        
        # 逻辑 B: 基于标点的合并逻辑
        # 如果 buffer 不为空，且不以结束标点结尾，说明段落被截断了，拼接空格+下一段
        elif buffer and not is_sentence_end(buffer):
            # 判断中英文环境决定加不加空格
            # 如果 buffer 结尾是中文，para 开头是中文，通常不需要空格，否则加空格
            if is_cjk(buffer[-1]) and is_cjk(para[0]):
                buffer += para
            else:
                buffer += " " + para
        
        else:
            # 如果 buffer 已经是完整段落（或 buffer 为空），先保存 buffer
            if buffer:
                merged_paragraphs.append(buffer)
            buffer = para

    # 循环结束后，处理最后的 buffer
    if buffer:
        merged_paragraphs.append(buffer)

    return merged_paragraphs

# --- 针对不同格式的提取 ---

def extract_txt(file_path: str) -> List[str]:
    content = ""
    # 尝试常见编码
    encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'latin-1']
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if not content:
        print(f"Error: Could not decode text file {file_path}")
        return []

    # TXT 处理策略：
    # 很多小说 TXT 是每一行一个硬回车，段落之间可能有空行，也可能没有。
    # 这里的策略是：按行分割，然后利用 post_process_text_list 进行语义/标点合并。
    raw_lines = content.splitlines()
    return post_process_text_list(raw_lines)

def clean_html_to_list(html_content: str) -> List[str]:
    """
    改进版 HTML 提取：
    确保 Trafilatura 提取的内容也经过 post_process_text_list 处理，
    以修复潜在的断行问题。
    """
    if not html_content:
        return []

    paragraphs = []

    # 方案 A: 使用 Trafilatura
    try:
        text_content = trafilatura.extract(html_content, include_comments=False, include_tables=False)
        if text_content:
            # 1. 仍然按行切分，去除空行
            raw_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            # 2. 【关键修改】将切分后的行传入 post_process_text_list 进行语义合并
            return post_process_text_list(raw_lines)
    except Exception:
        pass 

    # 方案 B: BeautifulSoup (保持不变)
    soup = BeautifulSoup(html_content, 'lxml')
    
    for script in soup(["script", "style", "head", "title", "meta", "iframe", "nav", "footer"]):
        script.extract()

    target_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']
    
    for element in soup.find_all(target_tags):
        text = element.get_text(separator=' ', strip=True)
        if text:
            paragraphs.append(text)
            
    return post_process_text_list(paragraphs)

def extract_pdf(file_path: str) -> List[str]:
    """
    改进版 PDF 提取：增加对 \r 和其他空白符的清洗
    """
    doc = fitz.open(file_path)
    raw_blocks = []
    
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        page_height = page.rect.height
        
        for b in blocks:
            if b[6] == 0:
                bbox = b[:4]
                text = b[4]
                
                # 页眉页脚过滤 (保持不变)
                if bbox[1] < page_height * 0.05 or bbox[3] > page_height * 0.94:
                    stripped_text = text.strip()
                    if stripped_text.isdigit(): 
                        continue
                    if len(stripped_text) < 5 and re.search(r'\d', stripped_text):
                        continue
                
                # 【关键修改】更彻底的清洗：同时替换 \n 和 \r，并去除多余空格
                # 先把 \n 和 \r 统一换成空格
                cleaned_text = text.replace('\n', ' ').replace('\r', ' ')
                # 清洗可能产生的连续空格（可选，但推荐）
                cleaned_block = " ".join(cleaned_text.split())
                
                if cleaned_block:
                    raw_blocks.append(cleaned_block)
    
    doc.close()
    return post_process_text_list(raw_blocks)

def extract_epub(file_path: str) -> List[str]:
    try:
        book = epub.read_epub(file_path)
        full_paragraphs = []

        # 遍历所有文档项
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content()
            chapter_paras = clean_html_to_list(content)
            full_paragraphs.extend(chapter_paras)
        
        return full_paragraphs
    except Exception as e:
        print(f"Error parsing EPUB: {str(e)}")
        return []

def extract_mobi(file_path: str) -> List[str]:
    """
    提取 MOBI 文本
    """
    temp_dir = "temp_mobi_extract"
    try:
        # 注意：mobi 库依赖某些系统环境，如果失败可能需要转换工具
        temp_dir, filepath = mobi.extract(file_path)
        full_paragraphs = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                raw_html = f.read()
                full_paragraphs = clean_html_to_list(raw_html)
        
        return full_paragraphs
    except Exception as e:
        print(f"Error parsing MOBI: {str(e)}")
        return []
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)