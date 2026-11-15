from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid, os, shutil
from functools import lru_cache

from app.core.database import get_db
from app.api.deps import get_current_user

from app.services.conv_services import process_user_message

# ===== ML pipelines =====
from app.llm.huberta import predict_speech_emotion
from app.llm.roberta import predict_emotion

# ===== ASR + Translation =====
import whisper
from deep_translator import GoogleTranslator
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
import json
router = APIRouter(prefix="/analyze", tags=["Analyze"])

@lru_cache(maxsize=1)
def get_whisper_model():
    return whisper.load_model("medium")


def speech_to_text_ml(audio_path: str) -> str:
    result = get_whisper_model().transcribe(audio_path, language="ml")
    return result["text"].strip()

def speech_to_text_en(audio_path: str) -> str:
    """
    English ASR using Whisper
    """
    result = get_whisper_model().transcribe(audio_path, language="en")
    return result["text"].strip()

def speech_to_text_auto(audio_path: str):
    result = get_whisper_model().transcribe(audio_path)
    text = result["text"].strip()
    detected_lang = result["language"]
    return text, detected_lang

def translate_ml_to_en(text: str) -> str:
    return GoogleTranslator(source="ml", target="en").translate(text)

import re

def detect_language_mix(text: str):
    malayalam_chars = re.findall(r'[\u0D00-\u0D7F]', text)
    english_words = re.findall(r'\b[a-zA-Z]+\b', text)

    mal_ratio = len(malayalam_chars) / max(len(text), 1)
    eng_ratio = len(english_words) / max(len(text.split()), 1)

    if mal_ratio > 0.1 and eng_ratio > 0.2:
        return "code_mixed"
    elif mal_ratio > 0.1:
        return "malayalam"
    else:
        return "english"

FILLER_WORDS = {
    "uh", "um", "ah", "like", "actually",
    "you know", "i mean", "okay", "so", "hmm"
}

def normalize_text(text: str):
    text = text.lower().strip()
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    text = re.sub(r'[^\w\s]', '', text)

    words = text.split()
    words = [w for w in words if w not in FILLER_WORDS]

    return " ".join(words)



@router.post("/{conversation_id}/audio")
async def analyze_audio(
    conversation_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    temp_file = f"tmp_{uuid.uuid4()}.wav"

    def save_upload() -> None:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    await run_in_threadpool(save_upload)

    try:
        
        whisper_model = await run_in_threadpool(get_whisper_model)
        result = await run_in_threadpool(
            whisper_model.transcribe,
            temp_file,
            task="translate",
            temperature=0,
        )

        transcribed_text=result["text"].strip()
        detected_lang = result["language"]

        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Empty transcription")
        if detected_lang == "ml":
            original_text = await run_in_threadpool(
                GoogleTranslator(source="en", target="ml").translate,
                transcribed_text,
            )
        else:
            original_text=transcribed_text      
        emotion = await run_in_threadpool(predict_speech_emotion, temp_file)
        normalized_text = await run_in_threadpool(normalize_text, transcribed_text)
        result = await run_in_threadpool(
            process_user_message,
            detected_lang=detected_lang,
            emotion=emotion,
            conversation_id=conversation_id,
            user_text=original_text,
            normalized_text=normalized_text,
            user=user,
            db=db,
        )

        assistant_reply = result["reply"]
            
        async def event_generator():
            yield f"data: {json.dumps({'transcript': transcribed_text})}\n\n"

            for token in assistant_reply.split():
                yield f"data: {json.dumps({'content': token + ' '})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

