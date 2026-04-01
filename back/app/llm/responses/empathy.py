from app.services.ai_service import call_mistral
# or: from incident_assistance.ai.mistral_client import call_mistral

def empathetic_response(user_text: str, incident_summary: str) -> str:
    prompt = f"""
You are a compassionate counselor.

Context:
{incident_summary}

User message:
"{user_text}"

Instructions:
- Respond with empathy
- Validate feelings
- Ask at most one gentle question
"""
    return call_mistral(prompt)
