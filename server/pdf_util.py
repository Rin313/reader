import fitz # PyMuPDF
import re
from typing import List, Dict, Optional
from collections import defaultdict
import statistics

def extract_pdf(
    pdf_path: str,
    header_footer_margin: float = 0.08,
    side_margin: float = 0.05,
    min_text_length: int = 3
) -> List[str]:
    """
    提取矢量PDF的正文内容
    
    功能:
    - 过滤批注、页眉页脚、水印等非正文内容
    - 智能处理跨页段落
    - 处理文本样式（字体大小变化）带来的影响
    - 使每个返回的字符串保持语义完整性
    
    Args:
        pdf_path: PDF文件路径
        header_footer_margin: 页眉页脚边距比例 (0-0.5)
        side_margin: 左右边距比例 (0-0.5)
        min_text_length: 最小文本长度，过滤过短内容
    
    Returns:
        字符串列表，每个元素是一个完整的段落
    """
    doc = fitz.open(pdf_path)
    
    # 第一遍：收集所有文本块和字体统计
    all_blocks = []
    font_size_counts = defaultdict(int)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 获取批注区域（用于排除）
        annot_rects = _get_annotation_rects(page)
        
        # 提取页面文本块
        page_blocks = _extract_page_blocks(
            page, page_num, header_footer_margin, side_margin, annot_rects
        )
        
        # 统计字体大小分布
        for block in page_blocks:
            font_size_counts[round(block['font_size'])] += len(block['text'])
        
        all_blocks.extend(page_blocks)
    
    doc.close()
    
    if not all_blocks:
        return []
    
    # 确定正文字体大小（出现次数最多的）
    body_font_size = max(font_size_counts.keys(), key=lambda x: font_size_counts[x])
    
    # 第二遍：合并段落，处理跨页
    paragraphs = _merge_paragraphs(all_blocks, body_font_size)
    
    # 后处理：清理和过滤
    result = []
    for para in paragraphs:
        cleaned = _clean_text(para)
        if len(cleaned) >= min_text_length:
            result.append(cleaned)
    
    return result


def _get_annotation_rects(page) -> List[fitz.Rect]:
    """获取页面所有批注的矩形区域"""
    annot_rects = []
    try:
        for annot in page.annots() or []:
            if annot.rect.is_valid and not annot.rect.is_empty:
                annot_rects.append(annot.rect)
    except Exception:
        pass
    return annot_rects


def _is_in_annotation(rect: fitz.Rect, annot_rects: List[fitz.Rect]) -> bool:
    """检查矩形是否与批注区域重叠"""
    for annot_rect in annot_rects:
        # 计算重叠比例
        intersect = rect & annot_rect
        if not intersect.is_empty:
            overlap_ratio = intersect.get_area() / rect.get_area() if rect.get_area() > 0 else 0
            if overlap_ratio > 0.5:  # 超过50%重叠则认为是批注内容
                return True
    return False


def _extract_page_blocks(
    page, 
    page_num: int,
    header_margin: float, 
    side_margin: float,
    annot_rects: List[fitz.Rect]
) -> List[Dict]:
    """提取页面的文本块，过滤无关内容"""
    rect = page.rect
    
    # 计算有效内容区域
    valid_rect = fitz.Rect(
        rect.width * side_margin,
        rect.height * header_margin,
        rect.width * (1 - side_margin),
        rect.height * (1 - header_margin)
    )
    
    blocks = []
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    
    for block in text_dict.get("blocks", []):
        # 只处理文本块
        if block.get("type") != 0:
            continue
        
        block_rect = fitz.Rect(block["bbox"])
        
        # 过滤不在有效区域的块
        if not valid_rect.intersects(block_rect):
            continue
        
        # 过滤批注区域的内容
        if _is_in_annotation(block_rect, annot_rects):
            continue
        
        # 提取文本和字体信息
        lines_data = []
        for line in block.get("lines", []):
            line_text = ""
            line_font_sizes = []
            
            for span in line.get("spans", []):
                text = span.get("text", "")
                font_size = span.get("size", 12)
                flags = span.get("flags", 0)
                
                # 过滤上标（通常是脚注引用标记）
                is_superscript = bool(flags & 1)
                
                # 过滤过小的字体（可能是水印或特殊标记）
                if font_size < 5:
                    continue
                
                if text.strip() and not is_superscript:
                    line_text += text
                    line_font_sizes.extend([font_size] * len(text))
            
            if line_text.strip():
                lines_data.append({
                    'text': line_text,
                    'font_sizes': line_font_sizes
                })
        
        if lines_data:
            # 合并行文本
            full_text = ' '.join(ld['text'] for ld in lines_data)
            all_font_sizes = []
            for ld in lines_data:
                all_font_sizes.extend(ld['font_sizes'])
            
            avg_font_size = statistics.mean(all_font_sizes) if all_font_sizes else 12
            
            blocks.append({
                'text': full_text,
                'font_size': avg_font_size,
                'page': page_num,
                'y_pos': block["bbox"][1],
                'x_pos': block["bbox"][0],
                'height': block["bbox"][3] - block["bbox"][1]
            })
    
    # 按位置排序（从上到下，从左到右）
    blocks.sort(key=lambda b: (round(b['y_pos'] / 20) * 20, b['x_pos']))
    
    return blocks


def _merge_paragraphs(blocks: List[Dict], body_font_size: float) -> List[str]:
    """合并文本块为完整段落"""
    if not blocks:
        return []
    
    paragraphs = []
    pending = ""
    last_block = None
    
    for block in blocks:
        text = block['text'].strip()
        if not text:
            continue
        
        font_size = block['font_size']
        
        # 标题检测：字体明显大于正文
        is_title = font_size > body_font_size + 2
        
        # 小字体内容可能是注释，但也可能是正文的一部分
        is_small = font_size < body_font_size - 3
        
        if is_title:
            # 标题作为独立段落
            if pending:
                paragraphs.append(pending)
                pending = ""
            paragraphs.append(text)
            last_block = block
            continue
        
        if is_small:
            # 小字体内容独立处理（可能是脚注等）
            if pending:
                paragraphs.append(pending)
                pending = ""
            paragraphs.append(text)
            last_block = block
            continue
        
        # 正文处理
        if pending and last_block:
            same_page = block['page'] == last_block['page']
            
            # 判断垂直间距（大间距可能是新段落）
            if same_page:
                y_gap = block['y_pos'] - (last_block['y_pos'] + last_block['height'])
                large_gap = y_gap > last_block['height'] * 1.5
            else:
                large_gap = False
            
            if large_gap:
                # 大间距，可能是新段落
                paragraphs.append(pending)
                pending = text
            elif _should_merge_blocks(pending, text, same_page):
                pending = _merge_texts(pending, text)
            else:
                paragraphs.append(pending)
                pending = text
        else:
            pending = text
        
        last_block = block
    
    if pending:
        paragraphs.append(pending)
    
    return paragraphs


def _should_merge_blocks(prev_text: str, next_text: str, same_page: bool) -> bool:
    """判断是否应该合并两个文本块"""
    prev_text = prev_text.rstrip()
    next_text = next_text.lstrip()
    
    if not prev_text or not next_text:
        return False
    
    last_char = prev_text[-1]
    first_char = next_text[0]
    
    # 连字符结尾（英文断词）-> 必须合并
    if last_char == '-':
        return True
    
    # 段落结束标点
    end_punct = '.!?。！？；'
    quote_end = '」』"）)\'"'
    
    # 明确的段落结束
    if last_char in end_punct:
        # 但如果下一段以小写开头，可能是异常断行
        if first_char.islower():
            return True
        return False
    
    if last_char in quote_end:
        # 引号结尾，检查前一个字符
        if len(prev_text) > 1 and prev_text[-2] in end_punct:
            return False
    
    # 下一段以小写字母开头 -> 很可能是句子续接
    if first_char.islower():
        return True
    
    # 中文处理
    is_prev_chinese = '\u4e00' <= last_char <= '\u9fff' or last_char in '，、：'
    is_next_chinese = '\u4e00' <= first_char <= '\u9fff'
    
    if is_prev_chinese and is_next_chinese:
        # 中文段落，逗号等非终止标点应合并
        if last_char not in '。！？；':
            return True
    
    # 跨页情况：更宽松的合并策略
    if not same_page:
        if first_char.islower():
            return True
        if is_next_chinese and last_char not in end_punct:
            return True
    
    return False


def _merge_texts(prev_text: str, next_text: str) -> str:
    """智能合并两段文本"""
    prev_text = prev_text.rstrip()
    next_text = next_text.lstrip()
    
    if not prev_text:
        return next_text
    if not next_text:
        return prev_text
    
    # 连字符断词：移除连字符直接连接
    if prev_text.endswith('-'):
        # 检查是否是真正的断词（非复合词）
        if next_text[0].islower():
            return prev_text[:-1] + next_text
        else:
            # 可能是复合词，保留连字符
            return prev_text + next_text
    
    # 判断语言决定连接方式
    last_char = prev_text[-1]
    first_char = next_text[0]
    
    # CJK字符不需要空格
    is_prev_cjk = '\u4e00' <= last_char <= '\u9fff' or last_char in '，。！？、；：""''（）'
    is_next_cjk = '\u4e00' <= first_char <= '\u9fff'
    
    if is_prev_cjk or is_next_cjk:
        return prev_text + next_text
    
    # 英文用空格连接
    return prev_text + ' ' + next_text


def _clean_text(text: str) -> str:
    """清理和规范化文本"""
    # 统一空白字符
    text = re.sub(r'[ \t]+', ' ', text)
    # 移除多余换行
    text = re.sub(r'\n{2,}', '\n', text)
    # 修复常见的 OCR 错误模式
    text = re.sub(r'\s+([,.\?!;:])', r'\1', text)
    # 清理首尾空白
    return text.strip()