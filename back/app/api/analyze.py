from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid, os, shutil

from app.core.database import get_db
from app.api.deps import get_current_user

# 🔁 Shared message pipeline
from app.services.message_service import handle_text_message
from app.services.conv_services import process_user_message

# ===== ML pipelines =====
from app.llm.huberta import predict_speech_emotion
from app.llm.roberta import predict_emotion

from app.models import Message

# ===== ASR + Translation =====
import whisper
from deep_translator import GoogleTranslator
from fastapi.responses import StreamingResponse
import json
import asyncio
router = APIRouter(prefix="/analyze", tags=["Analyze"])

# Load Whisper ONCE (CPU-safe)
whisper_model = whisper.load_model("medium")


def speech_to_text_ml(audio_path: str) -> str:
    result = whisper_model.transcribe(audio_path, language="ml")
    return result["text"].strip()

def speech_to_text_en(audio_path: str) -> str:
    """
    English ASR using Whisper
    """
    result = whisper_model.transcribe(audio_path, language="en")
    return result["text"].strip()

def speech_to_text_auto(audio_path: str):
    result = whisper_model.transcribe(audio_path)
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

    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        
        result = whisper_model.transcribe(
            temp_file,
            task="translate",   # Malayalam → English
            temperature=0       # More stable decoding
        )

        transcribed_text=result["text"].strip()
        detected_lang = result["language"]
        print("language",detected_lang)
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Empty transcription")
        if detected_lang == "ml":
            print("translating eng to ml audio user text")
            original_text = GoogleTranslator(
                        source="en",
                        target="ml"
                    ).translate(transcribed_text)  
        else:
            original_text=transcribed_text      
        # 2️⃣ Emotion
        # emotion = predict_speech_emotion(temp_file)
        # print("Emotion Detected:",emotion)
        emotion="Depressed"
        
        normalized_text = normalize_text(transcribed_text)
        print("norm",normalized_text)
        result = await process_user_message(
            detected_lang=detected_lang,
            emotion=emotion,
            conversation_id=conversation_id,
            user_text=original_text,
            normalized_text=normalized_text,
            user=user,
            db=db,
        )

        assistant_reply = result["reply"]
            
        # 4️⃣ STREAM RESPONSE (SSE)
        async def event_generator():
            # Optional: send transcription to frontend
            yield f"data: {json.dumps({'transcript': transcribed_text})}\n\n"

            # Stream assistant reply token by token
            for token in assistant_reply.split():
                yield f"data: {json.dumps({'content': token + ' '})}\n\n"
                await asyncio.sleep(0.03)

            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)



# @router.post("/{conversation_id}/audio")
# async def analyze_audio(
#     conversation_id: str,
#     file: UploadFile = File(...),
#     language: str = Form(...),
#     user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     if language not in ("en", "ml"):
#         raise HTTPException(status_code=400, detail="Invalid language")

#     temp_file = f"tmp_{uuid.uuid4()}.wav"

#     with open(temp_file, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         # 🇬🇧 English voice → HuBERT
#         if language == "en":
#             emotion = predict_speech_emotion(temp_file)

#             # 🔁 Inject TEXT into conversation
#             handle_text_message(
#                 conversation_id=conversation_id,
#                 user_text="[Voice message]",
#                 user=user,
#                 db=db,
#             )

#             return {
#                 "input_type": "english_audio",
#                 "emotion": emotion,
#             }

#         # 🇮🇳 Malayalam voice → ASR → Translate → RoBERTa
#         ml_text = speech_to_text_ml(temp_file)
#         en_text = translate_ml_to_en(ml_text)
#         emotions = predict_emotion(en_text)

#         # 🔁 Inject TRANSCRIBED TEXT into conversation
#         handle_text_message(
#             conversation_id=conversation_id,
#             user_text=en_text,
#             user=user,
#             db=db,
#         )

#         return {
#             "input_type": "malayalam_audio",
#             "original_text": ml_text,
#             "transcribed_text": en_text,
#             "emotions": emotions,
#         }

#     finally:
#         if os.path.exists(temp_file):
#             os.remove(temp_file)



# route to handle english text only rest all handles by coversation/messages route 
# by data from front
# @router.post("/{conversation_id}/audio")
# async def analyze_audio(
#     conversation_id: str,
#     file: UploadFile = File(...),
#     user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     temp_file = f"tmp_{uuid.uuid4()}.wav"

#     # 1️⃣ Save uploaded audio
#     with open(temp_file, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         # 2️⃣ English speech → text
#         transcribed_text = speech_to_text_en(temp_file)
#         # transcribed_text = "i have been beaten up"

#         if not transcribed_text:
#             raise HTTPException(status_code=400, detail="Empty transcription")

#         # 3️⃣ Emotion from HuBERT (audio-based)
#         emotion = predict_speech_emotion(temp_file)

#         # 4️⃣ Store REAL text in conversation (CRITICAL)
#         handle_text_message(
#             conversation_id=conversation_id,
#             user_text=transcribed_text,
#             user=user,
#             db=db,
#         )

#         # 5️⃣ Respond to frontend
#         return {
#             "input_type": "english_audio",
#             "transcribed_text": transcribed_text,
#             "emotion": emotion,
#         }

#     finally:
#         if os.path.exists(temp_file):
#             os.remove(temp_file)

# @router.post("/{conversation_id}/audio")
# async def analyze_audio(
#     conversation_id: str,
#     file: UploadFile = File(...),
#     user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     temp_file = f"tmp_{uuid.uuid4()}.wav"

#     with open(temp_file, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         # 1️⃣ Speech → Text
#         transcribed_text = speech_to_text_en(temp_file)
#         if not transcribed_text:
#             raise HTTPException(status_code=400, detail="Empty transcription")

#         # 2️⃣ Emotion
#         emotion = predict_speech_emotion(temp_file)

#         # 3️⃣ SAME PIPELINE AS TEXT
#         result = await process_user_message(
#             conversation_id=conversation_id,
#             user_text=transcribed_text,
#             user=user,
#             db=db,
#         )

#         return {
#             "input_type": "english_audio",
#             "transcribed_text": transcribed_text,
#             "emotion": emotion,
#             "assistant_reply": result["reply"],
#             "phase": result["phase"],
#         }

#     finally:
#         if os.path.exists(temp_file):
#             os.remove(temp_file)
