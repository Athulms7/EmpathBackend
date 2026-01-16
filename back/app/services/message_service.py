from sqlalchemy.orm import Session
from app.models import Conversation, Message, Incident
from app.services.incident_service import INCIDENT_TEMPLATE
from app.services.incident_service import(
    merge_entities,
    completion_percentage
)
from app.llm.incident_assistant import extract_entities


def handle_text_message(
    *,
    conversation_id: str,
    user_text: str,
    user,
    db: Session,
) -> Incident:
    """
    Shared logic for ALL user text inputs.
    (typed text OR voice-transcribed text)
    """

    user_text = (user_text or "").strip()
    if not user_text:
        raise ValueError("Empty user message")

    # 1️⃣ Validate conversation
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conversation:
        raise ValueError("Conversation not found")

    # 2️⃣ Save USER message
    db.add(
        Message(
            conversation_id=conversation_id,
            role="user",
            content=user_text,
        )
    )
    db.commit()

    # 3️⃣ Load or create Incident
    incident = (
        db.query(Incident)
        .filter_by(conversation_id=conversation_id)
        .first()
    )

    if not incident:
        incident = Incident(
            conversation_id=conversation_id,
            data=INCIDENT_TEMPLATE.copy(),
            completion_percentage=0.0,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

    # 4️⃣ Extract + merge entities
    extracted = extract_entities(user_text, incident.data)
    incident.data = merge_entities(dict(incident.data), extracted)

    # 5️⃣ Update completion %
    incident.completion_percentage = completion_percentage(incident.data)

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident
