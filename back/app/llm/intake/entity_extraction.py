from app.services.ai_service import call_mistral
import json

ENTITY_KEYS = [
    "suspect",
    "relationship_to_accused",
    "crime_location",
    "time_period",
    "frequency",
    "witnesses",
    "threat_present",
    "injury_present",
    "identity_known",
    "evidence_available",
    "medium",
    "secondary_action",
    "consent_present",
    "shared_residence",
    "workplace_related",
    "ongoing",
]

def extract_entities(message: str) -> dict:
    prompt = f"""
You are an information extraction system.

RULES:
- Return ONLY valid JSON
- Do NOT guess
- Omit missing fields

ALLOWED KEYS:
{ENTITY_KEYS}

MESSAGE:
"{message}"

OUTPUT JSON ONLY:
"""

    try:
        raw = call_mistral(prompt, temperature=0.0)

        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        return {k: v for k, v in data.items() if k in ENTITY_KEYS}

    except Exception as e:
        print("Entity extraction failed:", e)
        return {}
