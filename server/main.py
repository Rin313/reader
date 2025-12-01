import sys
import os
import shutil
import tempfile
import uvicorn
import webbrowser
from contextlib import asynccontextmanager
from typing import List, Dict, Callable

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from common import disable_quick_edit
from nlp_service import segment_text_content, find_vocab_matches
from text_processors import extract_pdf, extract_epub, extract_mobi, extract_txt
from translator import translate_text_wrapper
from tts import generate_audio_stream

# --- 配置 ---
HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"

FILE_EXTRACTORS: Dict[str, Callable[[str], List[str]]] = {
    ".txt": extract_txt,
    ".pdf": extract_pdf,
    ".epub": extract_epub,
    ".mobi": extract_mobi
}

# --- 生命周期管理 & 自动开启浏览器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("System starting up... Models loaded.")
    # 在服务启动时打开浏览器，避免阻塞
    try:
        webbrowser.open(BASE_URL)
        print(f"Browser opened at {BASE_URL}")
    except Exception as e:
        print(f"Failed to open browser: {e}")
    yield
    print("System shutting down...")

app = FastAPI(title="Doc Learner", lifespan=lifespan,openapi_url=None, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class SegmentRequest(BaseModel):
    text: str

class VocabMatchRequest(BaseModel):
    vocab_list: List[str]
    text_list: List[str]

class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    translator: str = "bing"
    from_lang: str = "auto"
    to_lang: str = "en"

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    translator: str
    status: str = "success"

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"

# --- Endpoints ---

@app.post("/upload")
def upload_and_extract(file: UploadFile = File(...)):
    # 优化：使用 set/dict 快速查找，降低复杂度
    filename = file.filename.lower()
    _, file_ext = os.path.splitext(filename)
    
    if file_ext not in FILE_EXTRACTORS:
        raise HTTPException(status_code=400, detail="Unsupported format.")

    # 创建临时文件
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    try:
        # 同步写入文件 (FastAPI 在 def 定义的路由中会使用线程池，不会阻塞主循环)
        with tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
        
        # 调用映射的处理函数
        extracted_lines = FILE_EXTRACTORS[file_ext](tmp_file.name)
        
        return {
            "filename": file.filename,
            "type": file_ext,
            "lines": extracted_lines,
            "total_lines": len(extracted_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # 确保清理临时文件
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)

@app.post("/segment")
def segment_sentence(request: SegmentRequest):
    # 简化判空逻辑
    if not request.text: return {"segments": []}
    try:
        return {"segments": segment_text_content(request.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seg failed: {str(e)}")

@app.post("/match_vocab")
def match_vocabulary(request: VocabMatchRequest):
    if not request.vocab_list or not request.text_list: return []
    try:
        return find_vocab_matches(request.vocab_list, request.text_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vocabulary matching failed: {str(e)}")

@app.post("/translate", response_model=TranslationResponse)
def translate_api(request: TranslationRequest):
    try:
        result = translate_text_wrapper(**request.model_dump())
        return TranslationResponse(
            original_text=request.text,
            translated_text=str(result),
            translator=request.translator
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trans failed: {str(e)}")

@app.post("/tts")
def tts_post_endpoint(request: TTSRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text required")

    return StreamingResponse(
        generate_audio_stream(request.text, request.voice, request.rate), 
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=tts_audio.mp3"}
    )

# 静态文件挂载放在最后，避免覆盖 API 路由
app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    disable_quick_edit()
    import multiprocessing
    multiprocessing.freeze_support()
    
    uvicorn.run(
        app, 
        host=HOST, 
        port=PORT, 
        reload=False, 
        log_level="info"
    )