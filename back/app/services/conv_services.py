
import json
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models import Conversation, Message, Incident

from app.services.incident_service import INCIDENT_TEMPLATE

# NLP / AI logic
from app.services.incident_service import  merge_entities
from app.services.incident_service import completion_percentage
from app.llm.incident_assistant import generate_next_question,extract_entities
from app.services.ai_service import call_mistral
from app.llm.incident_assistant import empathetic_response
from langdetect import detect
from deep_translator import GoogleTranslator
async def process_user_message(
    *,
    emotion:str,
    conversation_id: str,
    normalized_text:str,
    user_text: str,
    user,
    db: Session,
):
    # 1️⃣ Validate conversation
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 2️⃣ Save USER message
    db.add(Message(
        conversation_id=conversation_id,
        role="user",
        content=user_text
    ))
    db.commit()

    # 3️⃣ Load or create Incident
    incident = db.query(Incident).filter_by(
        conversation_id=conversation_id
    ).first()

    if not incident:
        incident = Incident(
            conversation_id=conversation_id,
            data=INCIDENT_TEMPLATE.copy()
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

    # 4️⃣ Extract + merge entities
    extracted = extract_entities(normalized_text, incident.data)
    incident.data = merge_entities(dict(incident.data), extracted)
    incident.completion_percentage = completion_percentage(incident.data)

    db.add(incident)
    db.commit()
    db.refresh(incident)

    # 🔹 INTAKE PHASE
    if incident.completion_percentage < 0.7:
        question = generate_next_question(incident.data)
        if question:
            db.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                content=question
            ))
            db.commit()

        return {
            "phase": "intake",
            "reply": question
        }

    # 🔹 SUMMARY PHASE
    if not incident.case_summary:
        prompt = f"""
Generate a clear, neutral, factual summary of the case.
Do not assume missing information.

Incident Data:
{json.dumps(incident.data, indent=2)}
"""

        summary = call_mistral(prompt).strip()
        if not summary:
            summary = (
                "Based on the information shared, a partial incident summary "
                "can be prepared, though some details remain unspecified."
            )

        incident.case_summary = summary
        db.add(incident)

        db.add(Message(
            conversation_id=conversation_id,
            role="assistant",
            content=summary
        ))
        db.commit()

        return {
            "phase": "summary",
            "reply": summary
        }

    # 🔹 SUPPORT / EMPATHY PHASE
    reply = empathetic_response(user_text, incident.case_summary)

    db.add(Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply
    ))
    db.commit()

    return {
        "phase": "support",
        "reply": reply
    }




def normalize_text(text: str) -> dict:
    try:
        lang = detect(text)
    except Exception:
        lang = "unknown"

    if lang != "en":
        translated = GoogleTranslator(
            source=lang,
            target="en"
        ).translate(text)
    else:
        translated = text

    return {
        "original_text": text,
        "english_text": translated,
        "language": lang
    }
