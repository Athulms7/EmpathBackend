# from fastapi import FastAPI
# from pydantic import BaseModel
# import requests

# app = FastAPI()

# LLAMA_URL = "http://localhost:8080/completion"

# class ChatRequest(BaseModel):
#     message: str

# @app.post("/chat")
# def chat(req: ChatRequest):
#     payload = {
#         "prompt": f"<s>[INST] {req.message} [/INST]",
#         "n_predict": 200,
#         "temperature": 0.7,
#         "top_p": 0.9
#     }

#     r = requests.post(LLAMA_URL, json=payload)
#     r.raise_for_status()

#     return {
#         "reply": r.json()["content"]
#     }


from fastapi import FastAPI
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from langdetect import detect
import requests

app = FastAPI()

LLAMA_URL = "http://localhost:8081/completion"

class ChatInput(BaseModel):
    message: str


def translate_to_english(text: str) -> str:
    return GoogleTranslator(source="ml", target="en").translate(text)


def translate_to_malayalam(text: str) -> str:
    return GoogleTranslator(source="en", target="ml").translate(text)


def call_llama(prompt: str) -> str:
    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "n_predict": 300,
        "temperature": 0.7,
        "top_p": 0.9
    }

    response = requests.post(LLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["content"]


@app.post("/chat")
async def chat(data: ChatInput):
    user_text = data.message.strip()

    if not user_text:
        return {"error": "Empty message"}

    # 1️⃣ Detect language
    try:
        lang = detect(user_text)
    except Exception:
        lang = "unknown"

    # 2️⃣ Translate Malayalam → English
    if lang == "ml":
        try:
            english_text = translate_to_english(user_text)
        except Exception as e:
            print("Translation failed:", e)
            english_text = user_text
    else:
        english_text = user_text

    # 3️⃣ Send to LLM (Mistral)
    try:
        ai_reply_en = call_llama(english_text)
    except Exception as e:
        return {"error": "LLM failed", "details": str(e)}

    # 4️⃣ Translate response back to Malayalam if needed
    if lang == "ml":
        try:
            ai_reply_final = translate_to_malayalam(ai_reply_en)
        except Exception:
            ai_reply_final = ai_reply_en
    else:
        ai_reply_final = ai_reply_en

    # 5️⃣ Final response
    return {
        "detected_language": lang,
        "user_message": user_text,
        "translated_to_english": english_text,
        "ai_response": ai_reply_final
    }
