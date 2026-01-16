import asyncio
import json
import requests
import os
from app.core.config import settings

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


# OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# def call_mistral(prompt: str) -> str:
#     try:
#         print("In openai call_mistral")
#         response = requests.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             json={
#                 "model": "mistralai/mistral-7b-instruct:free",
#                 "messages": [{"role": "user", "content": prompt}],
#             },
#             timeout=20,
#         )

#         if response.status_code != 200:
#             print("⚠️ OpenRouter non-200:", response.status_code)
#             return ""

#         data = response.json()
#         content = (
#             data.get("choices", [{}])[0]
#             .get("message", {})
#             .get("content", "")
#             .strip()
#         )

#         if not content:
#             print("⚠️ OpenRouter returned empty output")

#         return content

#     except Exception as e:
#         print("⚠️ OpenRouter call failed:", e)
#         return ""
