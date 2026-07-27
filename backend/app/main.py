import os
import tempfile
from contextlib import asynccontextmanager
from typing import Annotated
from pathlib import Path
import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import whisper

# Global variable to store the loaded model
model = None
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")

def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    td = datetime.timedelta(seconds=seconds)
    # td might not have hours if it's short, so we format it carefully
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds_int = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    # Load model on startup
    model = whisper.load_model(MODEL_SIZE)
    print("Model loaded successfully!")
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
    srt: str
    language: str

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Check extension if needed, though whisper handles most audio formats via ffmpeg
    ext = Path(file.filename).suffix.lower()
    
    # Save the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        temp_file.write(content)
        
    try:
        # Run whisper transcription
        print(f"Transcribing {file.filename}...")
        result = model.transcribe(temp_path)
        
        # Convert result segments to SRT format
        srt_content = ""
        for i, segment in enumerate(result["segments"], start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            
        return TranscribeResponse(srt=srt_content, language=result.get("language", "unknown"))
    except Exception as e:
        print(f"Error during transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/health")
def health_check():
    return {"status": "ok", "model": MODEL_SIZE}
