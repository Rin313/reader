import sys
import os
import shutil
import tempfile
import uvicorn
import webbrowser
import multiprocessing
import traceback
from contextlib import asynccontextmanager
from typing import List, Dict, Callable,Any

from fastapi import FastAPI, File, UploadFile, HTTPException,Body
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from common import disable_quick_edit_if_win,get_local_ip,get_app_path
from nlp_service import segment_text_content, find_vocab_matches
from text_processors import extract_with_language
from translator import translate_text_wrapper
from tts import generate_audio_stream
from storage import storage

# --- 配置 ---
HOST = "0.0.0.0"
PORT = 8000
BASE_URL = f"http://127.0.0.1:{PORT}"

# --- 生命周期管理 & 自动开启浏览器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("System starting up... Models loaded.")
    local_ip = get_local_ip()
    print("=" * 50)
    print(f"本机访问: http://127.0.0.1:{PORT}")
    print(f"局域网访问: http://{local_ip}:{PORT}")
    print("=" * 50)
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
    filename = file.filename.lower()
    _, file_ext = os.path.splitext(filename)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    try:
        with tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
        data=extract_with_language(tmp_file.name)
        storage.set('currentDoc', data)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
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
    try:
        vocab_list=storage.get('vocabs')
        if not vocab_list or not request.text_list: return []
        return find_vocab_matches(vocab_list, request.text_list)
    except Exception as e:
        traceback.print_exc()
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
@app.get("/api/storage/{key}")
async def get_item(key: str):
    return storage.get(key)
@app.put("/api/storage/{key}")
async def set_item(key: str, value: Any = Body(...)):
    storage.set(key, value)
static_dist_path = os.path.join(get_app_path(), "dist")
# 静态文件挂载放在最后，避免覆盖 API 路由
app.mount("/", StaticFiles(directory=static_dist_path, html=True), name="static")

if __name__ == "__main__":
    disable_quick_edit_if_win()
    multiprocessing.freeze_support()
    
    uvicorn.run(
        app, 
        host=HOST, 
        port=PORT, 
        reload=False, 
        workers=1
    )