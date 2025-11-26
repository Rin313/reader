import os
import shutil
import tempfile
import uvicorn
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nlp_service import segment_text_content, find_vocab_matches
from text_processors import extract_pdf, extract_epub, extract_mobi, extract_txt
from translator import translate_text_wrapper
from tts import generate_audio_stream , get_all_voices

# --- 生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("System starting up... All models loaded.")
    yield
    print("System shutting down...")

# --- 应用初始化 ---
app = FastAPI(
    title="Document Text Extractor & Learner",
    lifespan=lifespan,
    openapi_url=None, 
    docs_url=None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SegmentRequest(BaseModel):
    text: str

class VocabMatchRequest(BaseModel):
    vocab_list: List[str]
    text_list: List[str]

class TranslationRequest(BaseModel):
    text: str = Field(..., description="需要翻译的文本内容", min_length=1)
    translator: str = Field("bing", description="使用的翻译引擎")
    from_lang: str = Field("auto", description="源语言代码")
    to_lang: str = Field("en", description="目标语言代码")

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    translator: str
    status: str = "success"

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"

@app.post("/upload")
async def upload_and_extract(file: UploadFile = File(...)):
    filename = file.filename.lower()
    _, file_ext = os.path.splitext(filename)
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    file_path = tmp_file.name

    try:
        with tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
        
        extracted_lines: List[str] = []
        
        if file_ext == ".txt":
            extracted_lines = extract_txt(file_path)
        elif file_ext == ".pdf":
            extracted_lines = extract_pdf(file_path)
        elif file_ext == ".epub":
            extracted_lines = extract_epub(file_path)
        elif file_ext == ".mobi":
            extracted_lines = extract_mobi(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format.")
        
        return {
            "filename": file.filename,
            "type": file_ext,
            "lines": extracted_lines,
            "total_lines": len(extracted_lines)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except OSError:
            pass

@app.post("/segment")
async def segment_sentence(request: SegmentRequest):
    if not request.text:
        return {"segments": []} # 保持返回结构一致性
        
    try:
        result = segment_text_content(request.text)
        return {"segments": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.post("/match_vocab")
async def match_vocabulary(request: VocabMatchRequest):
    if not request.vocab_list or not request.text_list:
        return []

    try:
        # 如果并发量大，建议改为 def match_vocabulary 并让 FastAPI 放入线程池
        matches = find_vocab_matches(request.vocab_list, request.text_list)
        return matches

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vocabulary matching failed: {str(e)}")

@app.post("/translate", response_model=TranslationResponse)
def translate_api(request: TranslationRequest):
    try:
        result = translate_text_wrapper(
            text=request.text,
            translator=request.translator,
            from_lang=request.from_lang,
            to_lang=request.to_lang
        )
        
        return TranslationResponse(
            original_text=request.text,
            translated_text=str(result),
            translator=request.translator
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation Error: {str(e)}")

@app.get("/voices")
async def list_voices_endpoint():
    voices = await get_all_voices()
    return JSONResponse(content=voices)

@app.post("/tts")
async def tts_post_endpoint(request: TTSRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    audio_generator = generate_audio_stream(
        request.text,
        request.voice,
        request.rate,
        # request.volume,
        # request.pitch
    )

    return StreamingResponse(
        audio_generator, 
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=tts_audio.mp3"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, 
        access_log=True,
        log_level="info" 
    )