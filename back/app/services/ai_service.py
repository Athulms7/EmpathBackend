# import asyncio

# async def stream_ai_response(prompt: str):
#     fake_response = "This is a streamed AI response generated token by token."
#     for word in fake_response.split():
#         yield word + " "
#         await asyncio.sleep(0.2)

import asyncio
import json
import requests

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
