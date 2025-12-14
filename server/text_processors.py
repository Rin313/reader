import os
from typing import List, Dict
from lingua import Language, LanguageDetectorBuilder
from epub_util import extract_epub
from pdf_util import extract_pdf
from nlp_service import split_paragraphs
detector = LanguageDetectorBuilder.from_languages(
    Language.ENGLISH, Language.CHINESE
).build()
def detect_language(text: str) -> str:
    language = detector.detect_language_of(text)
    if language == Language.CHINESE:
        return 'zh'
    elif language == Language.ENGLISH:
        return 'en'
    return 'other' #数字会被识别为英语、中文之外，如果按中文处理，其他小语种也能享受到英文翻译，如果不处理，可以避免莫名其妙的翻译请求，如果额外处理，莫名其妙翻译请求的情况会加倍
def extract_with_language(file_path: str) -> List[Dict[str, str]]:
    _, file_ext = os.path.splitext(file_path.lower())
    # 提取文本段落
    if file_ext == '.txt':
        paragraphs = extract_txt(file_path)
    elif file_ext == '.pdf':
        paragraphs = split_paragraphs(extract_pdf(file_path))
    elif file_ext == '.epub':
        paragraphs = extract_epub(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")
    # 标记语言
    result = [
        {
            "text": para,
            "lang": detect_language(para)
        }
        for i, para in enumerate(paragraphs)
    ]
    return result
def extract_txt(file_path: str) -> List[str]:
    encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'latin-1']
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        # for 循环正常结束（所有编码都失败）才执行
        print(f"Error: Could not decode text file {file_path}")
        return []
    
    # 分割行并过滤空行（包括只有空白字符的行）
    return [line for line in content.splitlines() if line.strip()]
# def split_paragraphs(paragraphs, max_length=220):
#     """
#     对段落列表进行处理：
#     如果段落超过 max_length，则按句子边界进行拆分。
#     拆分后的每一部分都由完整的句子组成。
    
#     Args:
#         paragraphs (list[str]): 原始段落列表
#         max_length (int): 拆分阈值
        
#     Returns:
#         list[str]: 处理后的文本片段列表
#     """
#     result_segments = []

#     # 定义句子结束符的正则模式
#     # 包括中文句号、感叹号、问号，和英文的 . ? !
#     # (?<=...) 是后向断言，表示在这些符号“后面”进行分割，保留标点符号
#     sentence_pattern = r'(?<=[。！？.?!])\s*'

#     for text in paragraphs:
#         # 1. 预处理：去除首尾空白
#         text = text.strip()
#         if not text:
#             continue

#         # 2. 如果长度未超过阈值，直接保留
#         if len(text) <= max_length:
#             result_segments.append(text)
#             continue

#         # 3. 如果超过阈值，进行语义拆分
#         # 使用正则将段落拆分为句子列表
#         sentences = re.split(sentence_pattern, text)
        
#         current_chunk = ""
        
#         for sentence in sentences:
#             # 跳过空句子
#             if not sentence:
#                 continue
                
#             # 检查：(当前块 + 新句子) 是否会超过阈值
#             if len(current_chunk) + len(sentence) <= max_length:
#                 # 如果没超过，合并进去
#                 current_chunk += sentence
#             else:
#                 # 如果超过了，先保存当前的块
#                 if current_chunk:
#                     result_segments.append(current_chunk)
                
#                 # 开始新的块
#                 # 特殊情况处理：如果单个句子本身就超过了 max_length
#                 # 这里选择强制截断或者保留（通常为了完整性选择保留，尽管它超长了）
#                 if len(sentence) > max_length:
#                     result_segments.append(sentence)
#                     current_chunk = ""
#                 else:
#                     current_chunk = sentence
        
#         # 4. 循环结束后，处理最后一个遗留的块
#         if current_chunk:
#             result_segments.append(current_chunk)

#     return result_segments
# def is_sentence_end(text: str) -> bool:
#     """判断是否为句子结束"""
#     if not text: return True
#     # 英文句号，问号，感叹号，中文句号，问号，感叹号，冒号（有时候标题用冒号结尾）
#     endings = ('.', '!', '?', '。', '！', '？', '…', '"', '”', "'", '’')
#     return text.rstrip().endswith(endings)
# def is_cjk(char):
#     if not char: 
#         return False
#     return '\u4e00' <= char <= '\u9fff'
# def get_body_font_size(doc: fitz.Document, sample_pages=15) -> float:
#     """
#     统计正文标准字体大小。
#     采样页数增加，去掉最高频（可能是空白符）和最低频干扰，取众数。
#     """
#     font_sizes = []
#     page_count = len(doc)
#     # 采样前中后，覆盖更多样本
#     indices = list(range(min(page_count, sample_pages)))
#     if page_count > sample_pages:
#         indices.extend(range(page_count // 2, min(page_count, page_count // 2 + 5)))
    
#     for idx in indices:
#         page = doc[idx]
#         try:
#             blocks = page.get_text("dict")["blocks"]
#             for b in blocks:
#                 if "lines" in b:
#                     for line in b["lines"]:
#                         for span in line["spans"]:
#                             txt = span["text"].strip()
#                             # 排除空串和纯数字干扰
#                             if txt and not txt.isdigit(): 
#                                 font_sizes.append(round(span["size"], 1))
#         except:
#             pass
    
#     if not font_sizes:
#         return 11.0
    
#     try:
#         return statistics.mode(font_sizes)
#     except:
#         return font_sizes[0]

# class TextBlockState:
#     def __init__(self):
#         self.text = ""
#         self.font_size = 0.0
#         self.font_flags = 0
#         self.bbox = (0, 0, 0, 0)
#         self.page_num = -1

# def extract_pdf(file_path: str) -> List[str]: #为了正文的跨页合并，可能存在页眉页脚文本被过滤的问题
#     doc = fitz.open(file_path)
#     body_size = get_body_font_size(doc)
    
#     extracted_paragraphs = []
#     buffer = TextBlockState()
    
#     for page_idx, page in enumerate(doc):
#         page_height = page.rect.height
#         # sort=True 非常重要，保证阅读顺序
#         blocks = page.get_text("dict", sort=True)["blocks"]
        
#         for b in blocks:
#             if "lines" not in b: continue
            
#             # --- 1. 基础几何过滤 (粗筛) ---
#             bbox = b["bbox"]
#             # 这里的阈值放宽一点，交给后面的语义过滤去精细处理
#             if bbox[1] < page_height * 0.03 or bbox[3] > page_height * 0.97:
#                 continue
            
#             for line in b["lines"]:
#                 # 构建行文本和属性
#                 line_text_parts = []
#                 max_span_len = 0
#                 curr_size = 0.0
#                 curr_flags = 0
#                 curr_bbox = line["bbox"]
                
#                 for span in line["spans"]:
#                     txt = span["text"]
#                     # 替换换行符为空格
#                     txt = re.sub(r'[\n\r\t]', ' ', txt)
#                     if not txt.strip(): continue
                    
#                     line_text_parts.append(txt)
#                     if len(txt) > max_span_len:
#                         max_span_len = len(txt)
#                         curr_size = round(span["size"], 1)
#                         curr_flags = span["flags"]

#                 full_line_text = "".join(line_text_parts).strip()
#                 if not full_line_text: continue

#                 # --- 2. 语义级页眉页脚过滤 (精筛 - 关键步骤) ---
#                 # 即使过了几何过滤，如果位于页面边缘 且 字体大小不是正文，
#                 # 我们认为它是页眉/页脚/干扰项，直接跳过，**绝对不能 flush buffer**
                
#                 is_body_size = abs(curr_size - body_size) < 0.5
#                 is_top_region = curr_bbox[1] < page_height * 0.12
#                 is_bottom_region = curr_bbox[3] > page_height * 0.90
                
#                 # 如果是边缘区域，且字体大小和正文不一样 -> 视为干扰，静默跳过
#                 if (is_top_region or is_bottom_region) and not is_body_size:
#                     continue
                
#                 # 纯数字行（通常是页码），无论在哪里都跳过
#                 if full_line_text.isdigit() and len(full_line_text) < 6:
#                     continue

#                 # --- 3. 合并逻辑 ---
#                 should_merge = False
                
#                 if buffer.text:
#                     # 属性检查
#                     size_diff = abs(curr_size - buffer.font_size)
#                     is_same_size = size_diff < 0.5
#                     is_same_flags = (curr_flags == buffer.font_flags)
                    
#                     # 跨页检查
#                     is_cross_page = (page_idx > buffer.page_num)
                    
#                     if is_cross_page:
#                         # === 跨页合并核心修正 ===
#                         # 只有当样式一致时才考虑合并
#                         if is_same_size:
#                             # 1. 连字符结尾 -> 必连
#                             if buffer.text.strip().endswith('-'):
#                                 should_merge = True
#                             # 2. 上一段没结束 -> 必连 (这是解决被切断的关键)
#                             elif not is_sentence_end(buffer.text):
#                                 should_merge = True
#                             # 3. 如果上一段结束了(有句号)，通常不连，除非是某些紧凑排版
#                             # 但为了安全起见，跨页且有句号，我们视为新段落
#                             else:
#                                 should_merge = False
#                         else:
#                             # 样式不同（例如上一页结束是正文，下一页开始是标题），不连
#                             should_merge = False
                            
#                     else:
#                         # === 页内合并逻辑 ===
#                         v_distance = curr_bbox[1] - buffer.bbox[3]
                        
#                         # 判断是不是大标题（同大号字体，允许合并）
#                         is_heading = (curr_size > body_size * 1.1) and is_same_size
                        
#                         # 正常行距检查 (允许 0 到 1.6 倍行高)
#                         # 如果行距太大，可能是段落间距
#                         is_regular_line_spacing = 0 < v_distance < max(curr_size, buffer.font_size) * 1.6
                        
#                         if is_heading:
#                              # 标题分行，只要没隔太远，强制合并
#                             if v_distance < max(curr_size, buffer.font_size) * 3.0: 
#                                 should_merge = True
#                         elif is_same_size:
#                             # 正文合并
#                             if not is_sentence_end(buffer.text):
#                                 # 句子没结束，只要距离不过分大，就合并
#                                 if is_regular_line_spacing: 
#                                     should_merge = True
#                             else:
#                                 # 句子结束了。
#                                 # 检查是否有明显的段落首行缩进？
#                                 # 简单判断：如果当前行 x0 比上一行 x0 大出一个字符宽度，认为是缩进 -> 新段落
#                                 # 注意：这需要文本是对齐的（左对齐或两端对齐）
#                                 is_indented = curr_bbox[0] > buffer.bbox[0] + curr_size * 1.2
                                
#                                 if is_regular_line_spacing and not is_indented:
#                                     # 距离近，且没有缩进 -> 可能是同一段落
#                                     should_merge = True
#                                 else:
#                                     should_merge = False
#                         else:
#                             should_merge = False

#                 # --- 4. 执行操作 ---
#                 if should_merge:
#                     # 连接处理
#                     if buffer.text.endswith('-') and not buffer.text.endswith('--'):
#                         # 移除连字符
#                         if full_line_text and full_line_text[0].islower():
#                             buffer.text = buffer.text[:-1] + full_line_text
#                         else:
#                             buffer.text += full_line_text
#                     else:
#                         # 补空格
#                         if is_cjk(buffer.text[-1]) and is_cjk(full_line_text[0]):
#                             buffer.text += full_line_text
#                         else:
#                             buffer.text += " " + full_line_text
                    
#                     # 更新 buffer 状态（只更新位置信息，保持样式基准）
#                     buffer.bbox = curr_bbox
#                     buffer.page_num = page_idx
                    
#                 else:
#                     # 写入上一段
#                     if buffer.text:
#                         extracted_paragraphs.append(buffer.text)
                    
#                     # 重置 buffer
#                     buffer.text = full_line_text
#                     buffer.font_size = curr_size
#                     buffer.font_flags = curr_flags
#                     buffer.bbox = curr_bbox
#                     buffer.page_num = page_idx

#     # 循环结束，保存最后一段
#     if buffer.text:
#         extracted_paragraphs.append(buffer.text)

#     return split_paragraphs(clean_paragraphs(extracted_paragraphs))

# def clean_paragraphs(paragraphs: List[str]) -> List[str]:
#     cleaned = []
#     for p in paragraphs:
#         text = re.sub(r'\s+', ' ', p).strip()
#         if text:
#             cleaned.append(text)
#     return cleaned


# def post_process_text_list(paragraphs: List[str]) -> List[str]:
#     """
#     对提取出的初步段落列表进行二次清洗和合并。
#     解决：上一段没结束就换行的问题（PDF/TXT常见问题）。
#     """
#     merged_paragraphs = []
#     buffer = ""

#     for para in paragraphs:
#         para = para.strip()
#         if not para:
#             continue

#         # 处理 buffer 结尾的连字符 (Hyphenation) - 主要针对英文 PDF
#         if buffer and buffer.endswith('-') and not buffer.endswith('--'):
#             # 获取 buffer 的最后一个词（去除 -）和 para 的第一个词
#             # 简单的启发式策略：
#             # 1. 如果 para 首字母是小写 (ex: "inf-", "ormation") -> 合并为 "information"
#             # 2. 如果 para 首字母是大写 (ex: "pre-", "Covid") -> 可能是 "pre-Covid"，保留连字符
#             if para and para[0].islower():
#                 buffer = buffer[:-1] + para
#             else:
#                 # 保留连字符，直接拼接
#                 buffer += para
        
#         else:
#             # 如果 buffer 已经是完整段落（或 buffer 为空），先保存 buffer
#             if buffer:
#                 merged_paragraphs.append(buffer)
#             buffer = para

#     # 循环结束后，处理最后的 buffer
#     if buffer:
#         merged_paragraphs.append(buffer)

#     return merged_paragraphs