from fastapi import APIRouter, Depends,HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.incident import Incident
from app.services.ai_service import call_mistral
from app.services.incident_service import (
    INCIDENT_TEMPLATE,
    merge_entities,
    completion_percentage
)
from app.llm.incident_assistant import (
    extract_entities,
    ask_question,
    summarize_incident,
    generate_next_question,
    empathetic_response
)
from pydantic import BaseModel
from app.llm.roberta import predict_emotion
from app.services.conv_services import normalize_text, process_user_message
import json
import requests

LLAMA_URL = "http://localhost:8081/completion"
def call_llama(user_message: str, mode: str ) -> str:
    
    system_prompt="Act as a mental suppotive ai who knows all the legal sides about that. Try to ask questions to get the information to classify the case belongs like cyber crime, physical assult etc.And give the legal information and urther steps needed.Also don't ask all question at same time..eventually ask one by one. also donta generate as a huge paragrapgh..make it in a clear way which inculde some points and some short para"

    full_prompt = f"""
<s>[INST]
SYSTEM:
{system_prompt}

USER:
{user_message}
[/INST]
"""

    payload = {
        "prompt": full_prompt.strip(),
        "n_predict": 300,
        "temperature": 0.7,
        "top_p": 0.9
    }

    response = requests.post(LLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()

    return response.json()["content"]

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("")
def get_all(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {"conversations": db.query(Conversation).filter_by(user_id=user.id).all()}

@router.post("")
def create_conversation(data: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    convo = Conversation(user_id=user.id, title=data.get("title", "New Chat"))
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo

@router.get("/{id}/messages")
def get_messages(id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "messages": db.query(Message).join(Conversation)
        .filter(Conversation.user_id == user.id, Message.conversation_id == id)
        .all()
    }

class RenameConversationSchema(BaseModel):
    title: str


@router.patch("/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    payload: RenameConversationSchema,
    db: Session = Depends(get_db),
):
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.title = payload.title.strip()
    db.commit()

    return {"success": True}    



@router.post("/{id}/messages")
async def send_message(
    id: str,
    body: dict,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_text = body.get("content", "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")
    normalized = await run_in_threadpool(normalize_text, user_text)
    detected_lang=normalized["language"]
    emotion = await run_in_threadpool(predict_emotion, normalized["english_text"])
    # emotion="Depressed"
    async def stream():
        result = await run_in_threadpool(
            process_user_message,
            detected_lang=detected_lang,
            emotion=emotion,
            conversation_id=id,
            normalized_text=normalized["english_text"],
            user_text=user_text,
            user=user,
            db=db,
        )

        yield f"data: {json.dumps({'content': result['reply'], 'done': True})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )



    
@router.delete("/{id}")
def delete_conversation(
    id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == id,
            Conversation.user_id == user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()

    return {"success": True}


