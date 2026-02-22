"""
Central LLM logic for IncidentDB assistant

Responsibilities:
1. Extract structured entities from user messages
2. Ask targeted follow-up questions if data is incomplete
3. Generate a final contextual case summary
"""

# -----------------------------
# 1️⃣ ENTITY EXTRACTION (Mistral role)
# -----------------------------
import json
import requests
from app.services.ai_service import call_mistral 
LLAMA_URL = "http://localhost:8081/completion"

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


def extract_entities(message: str, current_state: dict) -> dict:
    """
    Uses Mistral to extract structured entities.
    Returns PARTIAL JSON (only detected fields).
    """

    prompt = f"""
You are an information extraction system.

TASK:
Extract entities from the user message.

RULES:
- Return ONLY valid JSON
- Extract entities if explicitly stated
- Extract entities if implicitly clear
- Do NOT guess
- Omit fields not mentioned

ALLOWED KEYS:
{ENTITY_KEYS}

EXAMPLES:

User: "He threatened me at my house"
Output:
{{"crime_location": "user residence"}}

User: "He threatened me at the office"
Output:
{{"crime_location": "workplace"}}

User: "He threatened me"
Output:
{{}}

USER MESSAGE:
"{message}"

OUTPUT JSON ONLY:
"""


    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "n_predict": 300,
        "temperature": 0.0,   # 🔴 CRITICAL: prevents guessing
        "top_p": 0.9,
    }

    try:
        response = requests.post(LLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()

        raw = response.json().get("content", "").strip()

        # 🧹 Clean common LLM mistakes
        raw = raw.replace("```json", "").replace("```", "").strip()
        print("LLM RAW OUTPUT:", raw)
        
        data = json.loads(raw)
        print("PARSED JSON:", data)

        # 🛡️ Safety filter: only allow known keys
        extracted = {
            k: v for k, v in data.items()
            if k in ENTITY_KEYS and v is not None
        }

        return extracted

    except Exception as e:
        # NEVER crash the pipeline
        print("Entity extraction failed:", e)
        return {}



# -----------------------------
# 2️⃣ FOLLOW-UP QUESTIONING (Mistral role)
# -----------------------------

def ask_question(incident_data: dict) -> str | None:
    asked = incident_data.get("asked_fields", [])

    priority_questions = [
        ("crime_location", "Where does this incident usually take place?"),
        ("time_period", "When did this situation first begin?"),
        ("frequency", "How often does this happen?"),
        ("witnesses", "Was anyone else present or aware of what happened?"),
        ("evidence_available", "Do you have any evidence such as messages or recordings?"),
        ("injury_present", "Have you been physically injured in any way?")
    ]

    for field, question in priority_questions:
        if incident_data.get(field) is None and field not in asked:
            # 🔴 REASSIGN list (not append)
            incident_data["asked_fields"] = asked + [field]
            return question

    # Final general question
    if not incident_data.get("final_question_asked", False):
        incident_data["final_question_asked"] = True
        return (
            "Is there anything else you’d like to share that you think is important "
            "or that we haven’t discussed yet?"
        )

    return None



# -----------------------------
# 3️⃣ CASE SUMMARY (Gemini / GPT role)
# -----------------------------

def summarize_incident(data: dict) -> str:
    """
    Generate a neutral, factual case summary.
    Replace with Gemini / GPT call later.
    """

    parts = []

    if data.get("relationship_to_accused"):
        parts.append(
            f"The incident involves a {data['relationship_to_accused']}."
        )

    if data.get("medium"):
        parts.append(
            f"The actions primarily occurred through {data['medium']} communication."
        )

    if data.get("frequency"):
        parts.append(
            f"The behavior occurred {data['frequency']}."
        )

    if data.get("threat_present") is True:
        parts.append("Threatening behavior has been reported.")

    if data.get("injury_present") is True:
        parts.append("Physical injury has been reported.")

    if data.get("ongoing") is True:
        parts.append("The situation is ongoing.")

    if not parts:
        return "The user has reported an incident and further details are being collected."

    return " ".join(parts)

def generate_next_question(incident_data: dict) -> str | None:
    asked = incident_data.get("asked_fields", [])

    # 🔴 EXCLUDE ALREADY ASKED FIELDS
    missing = [
        k for k, v in incident_data.items()
        if v is None
        and k not in asked
        and k not in ("asked_fields", "final_question_asked")
    ]

    if not missing:
        return None

    # Choose the MOST IMPORTANT missing field (first is OK for now)
    field_to_ask = missing[0]

    prompt = f"""
You are a calm, empathetic legal intake assistant.

Missing information:
{missing}

Instructions:
- Ask ONLY ONE question
- Ask specifically about: "{field_to_ask}"
- Be empathetic and non-judgmental
- Do NOT mention databases or fields

Ask a natural human question to collect it.
"""

    question = call_mistral(prompt).strip()
    print("RAW MISTRAL OUTPUT:", repr(question))
    # 🔴 IMPORTANT: reassign list (not append)
    incident_data["asked_fields"] = asked + [field_to_ask]
    
    return question

#this also works but with a check to give answer even without qns..
# def generate_next_question(incident_data: dict) -> str | None:
#     asked = incident_data.get("asked_fields", [])

#     missing = [
#         k for k, v in incident_data.items()
#         if v is None
#         and k not in asked
#         and k not in ("asked_fields", "final_question_asked")
#     ]

#     if not missing:
#         return None

#     field_to_ask = missing[0]

#     prompt = f"""
# You are a human legal intake assistant.

# IMPORTANT RULES:
# - Respond ONLY in plain English.
# - DO NOT return JSON.
# - DO NOT return key-value pairs.
# - DO NOT return structured data.
# - Ask exactly ONE question.
# - Do NOT explain anything.

# You need to collect information about: {field_to_ask}

# Example:
# If the missing field is "incident_date", you should respond:
# "When did the incident occur?"

# Now generate the question.
# """

#     question = call_mistral(prompt).strip()

#     print("RAW MISTRAL OUTPUT:", repr(question))

#     # 🚨 If model still outputs JSON → fallback
#     if question.startswith("{") or ":" in question:
#         fallback_map = {
#             "incident_date": "When did the incident occur?",
#             "location": "Where did the incident happen?",
#             "description": "Could you describe what happened?",
#             "identity_known": "Do you know who the person was?",
#             "crime_type": "Can you clarify what type of incident occurred?",
#         }
#         question = fallback_map.get(
#             field_to_ask,
#             "Could you please provide more details?"
#         )

#     incident_data["asked_fields"] = asked + [field_to_ask]

#     return question

def empathetic_response(user_text: str, incident_summary: str) -> str:
    prompt = f"""
You are a compassionate emotional support assistant.

Context of what the user has been through:
{incident_summary}

User message:
"{user_text}"

Instructions:
- Respond with empathy and understanding
- Validate the user’s feelings
- Do NOT give legal advice unless asked
- Do NOT interrogate
- Offer gentle support or reflection
- Ask at most one optional open-ended question
"""

    return call_mistral(prompt).strip()
