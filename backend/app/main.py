import os
import asyncio
import tempfile
import uuid
from contextlib import asynccontextmanager
from typing import Annotated
from pathlib import Path
import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from faster_whisper import WhisperModel

# Global variables
model = None
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")

# Simple in-memory task store
tasks = {}

def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds_int = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"Loading faster-whisper model '{MODEL_SIZE}'...")
    # Load faster-whisper model on startup
    # Use CPU by default if testing locally without GPU, otherwise it will fail.
    # In colab we have cuda. We'll wrap in try-except to fallback to cpu if needed.
    try:
        model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
        print("Model loaded successfully on CUDA!")
    except Exception as e:
        print(f"Failed to load on CUDA: {e}. Falling back to CPU...")
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        print("Model loaded successfully on CPU!")
    yield
    print("Shutting down...")

app = FastAPI(title="Whisper Colab API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscribeResponse(BaseModel):
    task_id: str
    message: str

class TaskStatusResponse(BaseModel):
    status: str
    srt: str | None = None
    language: str | None = None
    error: str | None = None

def process_transcription(task_id: str, temp_path: str, filename: str):
    try:
        tasks[task_id]["status"] = "processing"
        print(f"Task {task_id}: Transcribing {filename}...")
        
        segments, info = model.transcribe(temp_path, beam_size=5)
        
        srt_content = ""
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            text = segment.text.strip()
            
            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["srt"] = srt_content
        tasks[task_id]["language"] = info.language
        print(f"Task {task_id}: Completed.")
        
    except Exception as e:
        print(f"Task {task_id}: Error - {e}")
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    ext = Path(file.filename).suffix.lower()
    
    # Save the uploaded file to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_path = temp_file.name
    content = await file.read()
    temp_file.write(content)
    temp_file.close()
    
    task_id = uuid.uuid4().hex
    tasks[task_id] = {
        "status": "queued",
        "srt": None,
        "language": None,
        "error": None
    }
    
    # Run the processing in the background
    background_tasks.add_task(process_transcription, task_id, temp_path, file.filename)
    
    return TranscribeResponse(
        task_id=task_id, 
        message="Transcription task queued. Check status using /status/{task_id}"
    )

@app.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        status=tasks[task_id]["status"],
        srt=tasks[task_id]["srt"],
        language=tasks[task_id]["language"],
        error=tasks[task_id]["error"]
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "model": MODEL_SIZE}
