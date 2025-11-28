import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import trafilatura
import mobi
import os
import shutil
import re
import statistics
from typing import List, Dict, Tuple
# 必须保证每个段落不以换行符结尾
def is_sentence_end(text: str) -> bool:
    """判断是否为句子结束"""
    if not text: return True
    # 英文句号，问号，感叹号，中文句号，问号，感叹号，冒号（有时候标题用冒号结尾）
    endings = ('.', '!', '?', '。', '！', '？', '…', '"', '”', "'", '’')
    return text.rstrip().endswith(endings)
def is_cjk(char):
    if not char: 
        return False
    return '\u4e00' <= char <= '\u9fff'
def get_body_font_size(doc: fitz.Document, sample_pages=15) -> float:
    """
    统计正文标准字体大小。
    采样页数增加，去掉最高频（可能是空白符）和最低频干扰，取众数。
    """
    font_sizes = []
    page_count = len(doc)
    # 采样前中后，覆盖更多样本
    indices = list(range(min(page_count, sample_pages)))
    if page_count > sample_pages:
        indices.extend(range(page_count // 2, min(page_count, page_count // 2 + 5)))
    
    for idx in indices:
        page = doc[idx]
        try:
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            # 排除空串和纯数字干扰
                            if txt and not txt.isdigit(): 
                                font_sizes.append(round(span["size"], 1))
        except:
            pass
    
    if not font_sizes:
        return 11.0
    
    try:
        return statistics.mode(font_sizes)
    except:
        return font_sizes[0]

class TextBlockState:
    def __init__(self):
        self.text = ""
        self.font_size = 0.0
        self.font_flags = 0
        self.bbox = (0, 0, 0, 0)
        self.page_num = -1

def extract_pdf(file_path: str) -> List[str]: #为了正文的跨页合并，可能存在页眉页脚文本被过滤的问题
    doc = fitz.open(file_path)
    body_size = get_body_font_size(doc)
    
    extracted_paragraphs = []
    buffer = TextBlockState()
    
    for page_idx, page in enumerate(doc):
        page_height = page.rect.height
        # sort=True 非常重要，保证阅读顺序
        blocks = page.get_text("dict", sort=True)["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            # --- 1. 基础几何过滤 (粗筛) ---
            bbox = b["bbox"]
            # 这里的阈值放宽一点，交给后面的语义过滤去精细处理
            if bbox[1] < page_height * 0.03 or bbox[3] > page_height * 0.97:
                continue
            
            for line in b["lines"]:
                # 构建行文本和属性
                line_text_parts = []
                max_span_len = 0
                curr_size = 0.0
                curr_flags = 0
                curr_bbox = line["bbox"]
                
                for span in line["spans"]:
                    txt = span["text"]
                    # 替换换行符为空格
                    txt = re.sub(r'[\n\r\t]', ' ', txt)
                    if not txt.strip(): continue
                    
                    line_text_parts.append(txt)
                    if len(txt) > max_span_len:
                        max_span_len = len(txt)
                        curr_size = round(span["size"], 1)
                        curr_flags = span["flags"]

                full_line_text = "".join(line_text_parts).strip()
                if not full_line_text: continue

                # --- 2. 语义级页眉页脚过滤 (精筛 - 关键步骤) ---
                # 即使过了几何过滤，如果位于页面边缘 且 字体大小不是正文，
                # 我们认为它是页眉/页脚/干扰项，直接跳过，**绝对不能 flush buffer**
                
                is_body_size = abs(curr_size - body_size) < 0.5
                is_top_region = curr_bbox[1] < page_height * 0.12
                is_bottom_region = curr_bbox[3] > page_height * 0.90
                
                # 如果是边缘区域，且字体大小和正文不一样 -> 视为干扰，静默跳过
                if (is_top_region or is_bottom_region) and not is_body_size:
                    continue
                
                # 纯数字行（通常是页码），无论在哪里都跳过
                if full_line_text.isdigit() and len(full_line_text) < 6:
                    continue

                # --- 3. 合并逻辑 ---
                should_merge = False
                
                if buffer.text:
                    # 属性检查
                    size_diff = abs(curr_size - buffer.font_size)
                    is_same_size = size_diff < 0.5
                    is_same_flags = (curr_flags == buffer.font_flags)
                    
                    # 跨页检查
                    is_cross_page = (page_idx > buffer.page_num)
                    
                    if is_cross_page:
                        # === 跨页合并核心修正 ===
                        # 只有当样式一致时才考虑合并
                        if is_same_size:
                            # 1. 连字符结尾 -> 必连
                            if buffer.text.strip().endswith('-'):
                                should_merge = True
                            # 2. 上一段没结束 -> 必连 (这是解决被切断的关键)
                            elif not is_sentence_end(buffer.text):
                                should_merge = True
                            # 3. 如果上一段结束了(有句号)，通常不连，除非是某些紧凑排版
                            # 但为了安全起见，跨页且有句号，我们视为新段落
                            else:
                                should_merge = False
                        else:
                            # 样式不同（例如上一页结束是正文，下一页开始是标题），不连
                            should_merge = False
                            
                    else:
                        # === 页内合并逻辑 ===
                        v_distance = curr_bbox[1] - buffer.bbox[3]
                        
                        # 判断是不是大标题（同大号字体，允许合并）
                        is_heading = (curr_size > body_size * 1.1) and is_same_size
                        
                        # 正常行距检查 (允许 0 到 1.6 倍行高)
                        # 如果行距太大，可能是段落间距
                        is_regular_line_spacing = 0 < v_distance < max(curr_size, buffer.font_size) * 1.6
                        
                        if is_heading:
                             # 标题分行，只要没隔太远，强制合并
                            if v_distance < max(curr_size, buffer.font_size) * 3.0: 
                                should_merge = True
                        elif is_same_size:
                            # 正文合并
                            if not is_sentence_end(buffer.text):
                                # 句子没结束，只要距离不过分大，就合并
                                if is_regular_line_spacing: 
                                    should_merge = True
                            else:
                                # 句子结束了。
                                # 检查是否有明显的段落首行缩进？
                                # 简单判断：如果当前行 x0 比上一行 x0 大出一个字符宽度，认为是缩进 -> 新段落
                                # 注意：这需要文本是对齐的（左对齐或两端对齐）
                                is_indented = curr_bbox[0] > buffer.bbox[0] + curr_size * 1.2
                                
                                if is_regular_line_spacing and not is_indented:
                                    # 距离近，且没有缩进 -> 可能是同一段落
                                    should_merge = True
                                else:
                                    should_merge = False
                        else:
                            should_merge = False

                # --- 4. 执行操作 ---
                if should_merge:
                    # 连接处理
                    if buffer.text.endswith('-') and not buffer.text.endswith('--'):
                        # 移除连字符
                        if full_line_text and full_line_text[0].islower():
                            buffer.text = buffer.text[:-1] + full_line_text
                        else:
                            buffer.text += full_line_text
                    else:
                        # 补空格
                        if is_cjk(buffer.text[-1]) and is_cjk(full_line_text[0]):
                            buffer.text += full_line_text
                        else:
                            buffer.text += " " + full_line_text
                    
                    # 更新 buffer 状态（只更新位置信息，保持样式基准）
                    buffer.bbox = curr_bbox
                    buffer.page_num = page_idx
                    
                else:
                    # 写入上一段
                    if buffer.text:
                        extracted_paragraphs.append(buffer.text)
                    
                    # 重置 buffer
                    buffer.text = full_line_text
                    buffer.font_size = curr_size
                    buffer.font_flags = curr_flags
                    buffer.bbox = curr_bbox
                    buffer.page_num = page_idx

    # 循环结束，保存最后一段
    if buffer.text:
        extracted_paragraphs.append(buffer.text)

    return clean_paragraphs(extracted_paragraphs)

def clean_paragraphs(paragraphs: List[str]) -> List[str]:
    cleaned = []
    for p in paragraphs:
        text = re.sub(r'\s+', ' ', p).strip()
        if text:
            cleaned.append(text)
    return cleaned
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
    # 很多小说 TXT 是每一行一个硬回车，段落之间可能有空行，也可能没有。
    # 这里的策略是：按行分割，然后利用 post_process_text_list 进行语义/标点合并。
    raw_lines = content.splitlines()
    return post_process_text_list(raw_lines)

def clean_html_to_list(html_content: str) -> List[str]:
    """
    确保 Trafilatura 提取的内容也经过 post_process_text_list 处理，对提取出的初步段落列表进行二次清洗和合并，以修复潜在的断行问题。
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
            # 2. 将切分后的行传入 post_process_text_list 进行语义合并
            return post_process_text_list(raw_lines)
    except Exception as e:
        print(f"[Trafilatura Error]: {e}")  # 打印错误
        import traceback
        traceback.print_exc() # 打印详细堆栈
        pass 

    # 方案 B: BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')
    
    for script in soup(["script", "style", "head", "title", "meta", "iframe", "nav", "footer"]):
        script.extract()

    target_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']
    
    for element in soup.find_all(target_tags):
        text = element.get_text(separator=' ', strip=True)
        if text:
            paragraphs.append(text)
            
    return post_process_text_list(paragraphs)

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