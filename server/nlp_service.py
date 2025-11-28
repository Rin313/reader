import os
import spacy
from spacy.tokens import Doc
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

try:
    print("Loading NLP model (en_core_web_trf)...")
    nlp = spacy.load(os.getcwd()+'\\en_core_web_trf',disable=["ner"])
except OSError:
    print(f"Model load failed: {e}")
# 全局缓存
_CACHED_MATCHER = None
_CACHED_VOCAB_ID = None
# 两个接口无法同时执行
def find_vocab_matches(vocab_list, text_list):
    global _CACHED_MATCHER, _CACHED_VOCAB_ID
    
    current_vocab_id = hash(tuple(vocab_list)) 
    
    if _CACHED_MATCHER is None or _CACHED_VOCAB_ID != current_vocab_id:
        _CACHED_MATCHER = PhraseMatcher(nlp.vocab, attr="LEMMA")
        
        # 性能优化：生成 Pattern 时禁用 parser，只保留必要的组件以获取 lemma
        # en_core_web_trf 的 lemmatizer 需要 tagger，tagger 需要 transformer
        # 但 parser 是用于句法分析的，生成单个词的 lemma 时不需要
        with nlp.select_pipes(disable=["parser"]):
            patterns = list(nlp.pipe(vocab_list))
            
        _CACHED_MATCHER.add("VOCAB_LIST", patterns)
        _CACHED_VOCAB_ID = current_vocab_id

    results = []
    
    for doc in nlp.pipe(text_list):
        matches = _CACHED_MATCHER(doc)
        spans = [doc[start:end] for _, start, end in matches]
        filtered_spans = filter_spans(spans)
        
        doc_matches = []
        for span in filtered_spans:
            doc_matches.append({
                "start": span.start_char,
                "length": len(span.text),
                "matched_text": span.text,
                "vocab_lemma": span.lemma_ # 匹配到的词根
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