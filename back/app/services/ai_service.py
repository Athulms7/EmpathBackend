import asyncio
import json
import requests
import os
from app.core.config import settings
from groq import Groq

LLAMA_URL = "http://localhost:8081/completion"

async def stream_ai_response(prompt: str):
    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "n_predict": 300,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": True
    }

    loop = asyncio.get_running_loop()

    def make_request():
        return requests.post(
            LLAMA_URL,
            json=payload,
            stream=True,
            headers={"Content-Type": "application/json"},
        )

    response = await loop.run_in_executor(None, make_request)

    for line in response.iter_lines(chunk_size=1, decode_unicode=True):
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        token = data.get("content")
        if token:
            yield token
            await asyncio.sleep(0)


def call_mistral(prompt: str) -> str:
    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "n_predict": 300,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": False
    }

    response = requests.post(
        LLAMA_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60
    )

    response.raise_for_status()
    data = response.json()

    return data.get("content", "").strip()



# Load from environment variable
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def call_groq(prompt: str, temperature: float = 0.3) -> str:
    response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
            {"role": "system", "content": "You are a neutral legal incident summarizer."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content


# import google.generativeai as genai
# import os

# # Set API key from environment variable
# genai.configure(api_key=settings.GEMINI_API_KEY)

# def call_gemini(prompt: str, temperature: float = 0.3) -> str:
#     """
#     Simple Gemini text generation wrapper.
#     """

#     try:
#         model = genai.GenerativeModel("gemini-1.5-flash")

#         response = model.generate_content(
#             prompt,
#             generation_config={
#                 "temperature": temperature,
#                 "max_output_tokens": 800,
#             }
#         )

#         if not response.text:
#             return ""

#         return response.text.strip()

#     except Exception as e:
#         print("⚠️ Gemini call failed:", e)
#         return ""