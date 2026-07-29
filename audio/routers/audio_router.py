from fastapi import APIRouter, UploadFile, File
from services.ai_service import get_ai_service
import os
import shutil
import uuid
import datetime

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze-audio/")
async def analyze_audio(file: UploadFile = File(...)):
    """Accepts an audio file, runs offline AI analysis, and returns results."""
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    ai = get_ai_service()
    
    # 1. Run raw inference
    raw_transcription = ai.transcribe(file_path)
    sounds = ai.detect_sounds(file_path)
    
    # 2. Apply deterministic logic & get the cleaned output
    clean_transcription, analysis_text, is_alert = ai.analyze_context(raw_transcription, sounds)
    
    # Clean up the file to save disk space
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "transcription": clean_transcription,
        "detected_sounds": sounds,
        "alert_analysis": analysis_text,
        "alert_triggered": is_alert
    }