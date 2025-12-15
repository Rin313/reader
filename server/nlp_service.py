import os
from common import get_app_path
import spacy
from spacy.tokens import Doc
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans
try:
    print("Loading NLP model (en_core_web_lg)...")
    base_path = get_app_path()
    # 获取模型的绝对路径
    model_path_1 = os.path.join(base_path, "en_core_web_lg")
    model_path_2 = os.path.join(base_path, "xx_sent_ud_sm")
    nlp = spacy.load(model_path_1, disable=["ner"])
    print("Loading NLP model (xx_sent_ud_sm)...")
    nlp2 = spacy.load(model_path_2, disable=["ner"])
except Exception as e:
    print(f"Model load failed: {e}")
def split_paragraphs(texts: list[str], 
                     threshold: int = 240) -> list[str]:
    """
    遍历字符串列表，如果字符串长度大于阈值，则使用spacy进行分句
    
    Args:
        texts: 字符串列表
        threshold: 长度阈值
        model_name: spacy模型名称 (英文: en_core_web_sm, 中文: zh_core_web_sm)
    
    Returns:
        处理后的字符串列表（扁平化）
    """
    result = []
    for text in texts:
        if len(text) > threshold:
            # 使用spacy分句
            doc = nlp2(text)
            sentences = [sent.text.strip() for sent in doc.sents]
            result.extend(sentences)
        else:
            result.append(text)
    return result
# 全局缓存
_CACHED_MATCHER = None
_CACHED_VOCAB_ID = None
_CACHED_PATTERNS = None  # 新增：缓存 patterns 用于建立 lemma 映射


def find_vocab_matches(vocab_list, text_list):
    global _CACHED_MATCHER, _CACHED_VOCAB_ID, _CACHED_PATTERNS
    
    # 从 vocab_list 中提取 word 列表
    words = [item["word"] for item in vocab_list]
    
    # 使用 words 元组计算 hash（仅用于 Matcher 缓存）
    current_vocab_id = hash(tuple(words))
    
    # 判断是否需要重建 Matcher（仅当 words 变化时）
    if _CACHED_MATCHER is None or _CACHED_VOCAB_ID != current_vocab_id:
        _CACHED_MATCHER = PhraseMatcher(nlp.vocab, attr="LEMMA")
        # 生成 Pattern 时禁用 parser，只保留必要的组件以获取 lemma
        # en_core_web_trf 的 lemmatizer 需要 tagger，tagger 需要 transformer
        # 但 parser 是用于句法分析的，生成单个词的 lemma 时不需要
        _CACHED_PATTERNS = list(nlp.pipe(words, disable=["parser"], batch_size=1000))
        _CACHED_MATCHER.add("VOCAB_LIST", _CACHED_PATTERNS)
        _CACHED_VOCAB_ID = current_vocab_id
    
    # 每次都重新建立 lemma -> vocab_item 的映射（确保 meaning 是最新的）
    # 这个操作开销很小，不需要缓存
    lemma_map = {}
    for pattern, item in zip(_CACHED_PATTERNS, vocab_list):
        # pattern 是 Doc 对象，需要遍历 tokens 获取 lemma
        lemma_key = " ".join([token.lemma_ for token in pattern]).lower()
        if lemma_key not in lemma_map:
            lemma_map[lemma_key] = item

    results = []
    
    for doc in nlp.pipe(text_list, batch_size=100):
        matches = _CACHED_MATCHER(doc)
        spans = [doc[start:end] for _, start, end in matches]
        filtered_spans = filter_spans(spans)
        
        doc_matches = []
        for span in filtered_spans:
            # Span 对象有 lemma_ 属性，会自动拼接所有 token 的 lemma
            lemma_key = span.lemma_.lower()
            vocab_item = lemma_map.get(lemma_key, {})
            
            doc_matches.append({
                "start": span.start_char,
                "length": len(span.text),
                "matched_text": span.text,
                "vocab_lemma": span.lemma_,
                "word": vocab_item.get("word", ""),
                "meaning": vocab_item.get("meaning", "")
            })
        
        results.append(doc_matches)

    return results
def segment_text_content(text: str) -> list:
    if not nlp or not text.strip():
        return []

    doc = nlp(text)
    structured_results = []

    for sent in doc.sents:
        # 跳过空白的句子
        if not sent.text.strip():
            continue
        segments = process_sentence_segmentation(sent)
        structured_results+=segments
    return structured_results

def process_sentence_segmentation(sent) -> list:
    """
    引入依存关系判断，避免将名词列表和短语切碎。
    """
    if len(sent) < 6:
        return [sent.text.strip()]

    segments = []
    current_chunk = []
    
    # 缓冲区最小长度（Token数）
    min_chunk_len = 3 

    for i, token in enumerate(sent):
        # =================================================
        # 逻辑 A：判断是否在当前词【之前】切分
        # =================================================
        split_before = False
        
        # 1. 连词 (CCONJ/SCONJ) 处理
        if token.pos_ in ["CCONJ", "SCONJ"]:
            # 优化：只有当连词连接的是句子层面（连接动词）或者引导从句时才切
            # 如果 'and' 连接的是两个名词 (bread and butter)，head 通常是名词，dep 是 cc
            # 简单的判断：如果连词的 head 是名词，通常是列表，不切。
            is_phrase_conjunction = token.head.pos_ in ["NOUN", "PROPN", "ADJ", "ADV"]
            
            if not is_phrase_conjunction:
                if len(current_chunk) >= min_chunk_len and i > 0:
                    split_before = True

        # 2. 关系词 (which, who, that...)
        elif token.tag_ in ["WDT", "WP", "WP$", "WRB"]:
             if len(current_chunk) >= min_chunk_len and i > 0:
                split_before = True
        
        # 3. 长介词短语
        elif token.pos_ == "ADP" and len(current_chunk) > 8:
             split_before = True

        if split_before:
            segment_text = "".join(current_chunk).strip()
            if segment_text:
                segments.append(segment_text)
            current_chunk = []

        # 将当前词加入缓冲区
        current_chunk.append(token.text_with_ws)
        
        # =================================================
        # 逻辑 B：判断是否在当前词【之后】切分 (标点处理)
        # =================================================
        split_after = False
        
        if token.text in [",", ";", ":", "—"]:
            is_comma = (token.text == ",")
            
            # 优化：列表检测 (List Detection)
            # 如果是逗号，且它连接的是并列名词 (dependency label 通常为 punct，且父节点有 conj 孩子)
            # 或者简单判断：如果逗号后面紧跟着连词(and/or)或者名词，且前面也是名词，大概率是列表
            
            is_list_comma = False
            if is_comma:
                # 获取下一个非空白 token
                next_token = sent[i+1] if i+1 < len(sent) else None
                # 如果逗号后面紧跟由并列连词引导的部分，或者逗号连接两个名词，视为列表
                if next_token and token.head.pos_ in ["NOUN", "PROPN", "ADJ"]:
                    # 只有当缓冲区很短时，我们才极力保护列表。
                    # 如果缓冲区已经很长了（比如 > 10），即使是列表也切一下吧，不然太长了。
                    if len(current_chunk) < 10: 
                        is_list_comma = True

            if not is_list_comma:
                # 只有缓冲区有内容才切
                if len(current_chunk) > 0:
                    split_after = True
        
        if split_after:
            segment_text = "".join(current_chunk).strip()
            if segment_text:
                segments.append(segment_text)
            current_chunk = []

    # 处理剩余部分
    if current_chunk:
        segment_text = "".join(current_chunk).strip()
        if segment_text:
            segments.append(segment_text)

    if not segments:
        return [sent.text.strip()]
        
    return segments