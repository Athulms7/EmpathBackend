import requests

LLAMA_URL = "http://localhost:8081/completion"

def call_mistral(prompt: str, temperature=0.7, max_tokens=256) -> str:
    payload = {
        "prompt": prompt,
        "temperature": temperature,
        "n_predict": max_tokens,
        "top_p": 0.9,
    }

    response = requests.post(LLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    return response.json()["content"].strip()
