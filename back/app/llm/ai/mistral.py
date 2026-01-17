import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

LOCAL_DIR = "./mistral7b_local"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(LOCAL_DIR)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    LOCAL_DIR,
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    device_map="auto"
)


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_response(
    user_input: str,
    history: list,
    system_prompt_path: str,
    text_emotion: str | None,
    voice_emotion: str | None
):
    base_prompt = load_prompt(system_prompt_path)

    if "{text_emotion}" in base_prompt:
        base_prompt = base_prompt.format(
            text_emotion=text_emotion or "unknown",
            voice_emotion=voice_emotion or "unknown"
        )

    messages = [{"role": "system", "content": base_prompt}]

    for u, a in history:
        messages.append({"role": "user", "content": u})
        messages.append({"role": "assistant", "content": a})

    messages.append({"role": "user", "content": user_input})

    tokenized = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        output = model.generate(
            tokenized,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    return tokenizer.decode(
        output[0][len(tokenized[0]):],
        skip_special_tokens=True
    ).strip()
