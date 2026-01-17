from incident_assistance.ai.mistral import generate_response

def empathetic_response(user_text, summary, history, emotions):
    prompt = f"""
You are a compassionate counselor.

Context:
{summary}

User message:
"{user_text}"

Respond with empathy and validation.
"""

    return generate_response(
        user_input=user_text,
        history=history,
        system_prompt_path="incident_assistance/prompts/normal.txt",
        text_emotion=emotions.get("text"),
        voice_emotion=emotions.get("voice")
    )
