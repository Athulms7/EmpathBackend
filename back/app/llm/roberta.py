import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ================= CONFIG =================
MODEL_DIR = "F:\empathai_ter_model"
PREDICTION_THRESHOLD = 0.5
# ==========================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===== LOAD ONCE (IMPORTANT) =====
print("🔹 Loading TER tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=False
)

print("🔹 Loading TER model...")
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

print(f"✅ TER model loaded on {device}")


def predict_emotion(text: str) -> dict:
    """
    Predict emotions from English text.
    """
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.sigmoid(logits).squeeze().cpu().numpy()

    results = {}
    for i, p in enumerate(probs):
        if p > PREDICTION_THRESHOLD:
            label = model.config.id2label[i]
            results[label] = round(float(p), 4)

    return results
