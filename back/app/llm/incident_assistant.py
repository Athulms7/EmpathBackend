"""
Central LLM logic for IncidentDB assistant

Responsibilities:
1. Extract structured entities
2. Infer context automatically
3. Ask intelligent follow-up questions
4. Generate empathetic responses
5. Produce incident summaries
"""

import json
import requests
from app.services.ai_service import call_mistral

LLAMA_URL = "http://localhost:8081/completion"


# -----------------------------
# ENTITY SCHEMA
# -----------------------------

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


# -----------------------------
# ENTITY EXTRACTION
# -----------------------------

def extract_entities(message: str, current_state: dict) -> dict:

    prompt = f"""
You are an information extraction system.

Extract structured information from the message.

RULES
- Return ONLY JSON
- Do not guess
- Omit fields not mentioned

Allowed keys:
{ENTITY_KEYS}

For medium ONLY allow:
"physical" or "online"

Examples:

User: "He hit me"
Output:
{{"medium":"physical"}}

User: "He sent threatening messages"
Output:
{{"medium":"online"}}

User message:
"{message}"

Return JSON only.
"""

    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "n_predict": 300,
        "temperature": 0.0,
        "top_p": 0.9,
    }

    try:

        response = requests.post(LLAMA_URL, json=payload, timeout=120)
        raw = response.json().get("content", "").strip()

        raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)

        extracted = {
            k: v for k, v in data.items()
            if k in ENTITY_KEYS and v is not None
        }

        return extracted

    except Exception as e:
        print("Entity extraction failed:", e)
        return {}


# -----------------------------
# NORMALIZE ENTITIES
# -----------------------------

def normalize_entities(data: dict):

    if "injury_present" in data:
        val = str(data["injury_present"]).lower()
        data["injury_present"] = val in ["yes", "true"]

    if "identity_known" in data:
        if data["identity_known"]:
            data["identity_known"] = True

    if data.get("relationship_to_accused") == "spouse":
        data["relationship_to_accused"] = "husband"

    return data


def apply_context_rules(incident_data: dict, message: str):

    text = message.lower()

    physical_keywords = [
        "hit","beat","beaten","slap","punched","kick",
        "assault","violence","hurt","abuse","torture",
        "ragging","bully","bullying","body shaming",
        "forced","humiliated"
    ]

    online_keywords = [
        "message","text","chat","instagram",
        "facebook","email","online","whatsapp",
        "telegram","snapchat"
    ]

    # Only set if clearly physical
    if any(word in text for word in physical_keywords):
        incident_data["medium"] = "physical"

    # Only set if clearly online
    elif any(word in text for word in online_keywords):
        incident_data["medium"] = "online"

    # Otherwise DO NOTHING (leave medium None)

    # Relationship inference
    if "husband" in text:
        incident_data["relationship_to_accused"] = "husband"

    if "senior" in text or "seniors" in text:
        incident_data["relationship_to_accused"] = "senior students"

    if "boss" in text:
        incident_data["relationship_to_accused"] = "employer"
        incident_data["workplace_related"] = True

# -----------------------------
# INCIDENT TYPE DETECTION
# -----------------------------

def detect_incident_type(message: str, data: dict):

    text = message.lower()

    if data.get("relationship_to_accused") in ["husband","wife","partner"]:
        return "domestic_violence"

    if data.get("workplace_related"):
        return "workplace_harassment"

    if data.get("medium") == "online":
        return "online_harassment"

    if data.get("medium") == "physical":
        return "physical_assault"

    return "unknown"


# -----------------------------
# FOLLOW-UP QUESTIONS
# -----------------------------

QUESTION_BANK = {

    "domestic_violence": [
        ("crime_location","Where do these incidents usually happen?"),
        ("frequency","How often has this been happening?"),
        ("shared_residence","Do you currently live in the same residence?")
    ],

    "physical_assault":[
        ("crime_location","Where did this incident take place?"),
        ("witnesses","Did anyone see what happened?")
    ],

    "online_harassment":[
        ("evidence_available","Do you still have the messages or screenshots?")
    ],

    "unknown":[
        ("crime_location","Where did this incident happen?"),
        ("time_period","When did this start?")
    ]
}


def ask_question(incident_data: dict):

    asked = incident_data.get("asked_fields", [])

    incident_type = incident_data.get("incident_type","unknown")

    questions = QUESTION_BANK.get(incident_type, QUESTION_BANK["unknown"])

    for field, question in questions:

        if incident_data.get(field) is None and field not in asked:

            incident_data["asked_fields"] = asked + [field]

            return question

    return None


# -----------------------------
# EMPATHETIC RESPONSE
# -----------------------------

def generate_next_question(incident_data: dict, user_text: str, emotion: str):

    question = ask_question(incident_data)

    if not emotion:
        emotion = "distress"

    prompt = f"""
You are a compassionate counselor.

User message:
"{user_text}"

Detected emotion:
{emotion}

Known case data:
{json.dumps({k:v for k,v in incident_data.items() if v is not None}, indent=2)}

Respond with empathy.

First acknowledge the user's feelings.

Then reassure them they can speak at their own pace.

Then naturally ask:

"{question}"

Rules:
- No numbering
- No bullet points
- Sound human
- Keep response under 4 sentences
"""

    return call_mistral(prompt).strip()


# -----------------------------
# EMPATHETIC SUPPORT (Fix ImportError)
# -----------------------------

def empathetic_response(user_text: str, incident_summary: str):

    prompt = f"""
You are a compassionate emotional support assistant.

Context:
{incident_summary}

User message:
"{user_text}"

Respond with empathy and validation.

Do not interrogate.
Ask at most one gentle question.
"""

    return call_mistral(prompt).strip()


# -----------------------------
# INCIDENT SUMMARY
# -----------------------------

def summarize_incident(data: dict):

    parts = []

    if data.get("relationship_to_accused"):
        parts.append(f"The incident involves the user's {data['relationship_to_accused']}.")

    if data.get("medium"):
        parts.append(f"The incident occurred through {data['medium']} interaction.")

    if data.get("frequency"):
        parts.append(f"The behavior occurred {data['frequency']}.")

    if data.get("injury_present"):
        parts.append("Physical injury has been reported.")

    if data.get("ongoing"):
        parts.append("The situation appears ongoing.")

    if not parts:
        return "An incident has been reported and further details are being collected."

    return " ".join(parts)


# -----------------------------
# MAIN PIPELINE
# -----------------------------

def process_user_message(message: str, incident_data: dict, emotion: str):

    extracted = extract_entities(message, incident_data)

    extracted = normalize_entities(extracted)

    incident_data.update(extracted)

    apply_context_rules(incident_data, message)

    incident_data["incident_type"] = detect_incident_type(message, incident_data)

    response = generate_next_question(
        incident_data,
        message,
        emotion
    )

    return response