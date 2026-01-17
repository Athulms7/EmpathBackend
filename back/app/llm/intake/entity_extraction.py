import json
import requests

LLAMA_URL = "http://localhost:8081/completion"

ENTITY_KEYS = [
    "relationship_to_accused", "crime_location", "time_period",
    "frequency", "witnesses", "threat_present",
    "injury_present", "evidence_available", "ongoing"
]


def extract_entities(message: str) -> dict:
    prompt = f"""
Extract factual entities from the message.

Rules:
- Output ONLY JSON
- Do not guess
- Omit missing fields

Allowed keys:
{ENTITY_KEYS}

Message:
"{message}"
"""

    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "temperature": 0.0,
        "n_predict": 300
    }

    try:
        res = requests.post(LLAMA_URL, json=payload, timeout=60)
        raw = res.json()["content"]
        data = json.loads(raw)
        return {k: v for k, v in data.items() if k in ENTITY_KEYS}
    except Exception:
        return {}
