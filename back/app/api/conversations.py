from fastapi import APIRouter, Depends,HTTPException
from fastapi.responses import StreamingResponse
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
from app.llm.roberta import predict_emotion
from app.services.conv_services import normalize_text, process_user_message
import json
import requests
import asyncio

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

# @router.post("/{id}/messages")
# def send_message(
#     id: str,
#     body: dict,
#     user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     user_text = body.get("content", "").strip()
#     if not user_text:
#         raise HTTPException(status_code=400, detail="Empty message")

#     # 1️⃣ Validate conversation
#     conversation = db.query(Conversation).filter_by(id=id).first()
#     if not conversation:
#         raise HTTPException(status_code=404, detail="Conversation not found")

#     # 2️⃣ Save USER message
#     db.add(Message(
#         conversation_id=id,
#         role="user",
#         content=user_text
#     ))
#     db.commit()

#     # 3️⃣ Load or create Incident
#     incident = db.query(Incident).filter_by(conversation_id=id).first()
#     if not incident:
#         incident = Incident(
#             conversation_id=id,
#             data=INCIDENT_TEMPLATE.copy()
#         )
#         db.add(incident)
#         db.commit()
#         db.refresh(incident)

#     # 4️⃣ Extract + merge entities (FIRST MESSAGE INCLUDED)
#     extracted = extract_entities(user_text, incident.data)
#     incident.data = merge_entities(dict(incident.data), extracted)
#     incident.completion_percentage = completion_percentage(incident.data)
#     db.add(incident)
#     db.commit()
#     db.refresh(incident)

#     # ----------------------------------------------------
#     # STREAMING GENERATOR (SSE)
#     # ----------------------------------------------------
#     async def stream():

#         # 🔹 INTAKE PHASE
#         if incident.completion_percentage < 0.7:
#             question = generate_next_question(incident.data)

#             db.add(incident)
#             db.commit()
#             db.refresh(incident)

#             if question:
#                 db.add(Message(
#                     conversation_id=id,
#                     role="assistant",
#                     content=question
#                 ))
#                 db.commit()

#             yield f"data: {json.dumps({'content': question or '', 'done': True})}\n\n"
#             return

#         # 🔹 SUMMARY PHASE (ONLY ONCE)
#         if not incident.case_summary:
#             prompt = f"""
#         Generate a clear, neutral, factual summary of the case.
#         Do not assume missing information.

#         Incident Data:
#         {json.dumps(incident.data, indent=2)}
#         """

#             summary = call_mistral(prompt)

#             if not summary.strip():
#                 summary = (
#                     "Based on the information shared, a partial incident summary "
#                     "can be prepared, though some details remain unspecified."
#                 )

#             incident.case_summary = summary.strip()

#             db.add(incident)
#             db.add(Message(
#                 conversation_id=id,
#                 role="assistant",
#                 content=incident.case_summary
#             ))
#             db.commit()

#             # send summary as a single SSE message
#             yield f"data: {json.dumps({'content': incident.case_summary, 'done': True})}\n\n"
#             return



#         # 🔹 SUPPORT / EMPATHY PHASE (FOREVER)
#         reply = empathetic_response(user_text, incident.case_summary)

#         db.add(Message(
#             conversation_id=id,
#             role="assistant",
#             content=reply
#         ))
#         db.commit()

#         yield f"data: {json.dumps({'content': reply, 'done': True})}\n\n"

#     return StreamingResponse(
#         stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#         }
#     )


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
    normalized = normalize_text(user_text)
    print(normalized)
    # emotion=predict_emotion(normalized["english_text"])
    emotion="Depressed"
    # print("Emotion Detected:",emotion)
    async def stream():
        result = await process_user_message(
            emotion=emotion,
            conversation_id=id,
            normalized_text=normalized,
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
