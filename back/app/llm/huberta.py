import torch
import librosa
import os
from transformers import AutoFeatureExtractor, HubertForSequenceClassification

# ================= CONFIG =================
MODEL_DIR = "F:\empathai_ser_model_hubert"
TARGET_SR = 16000
# ==========================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===== LOAD ONCE =====
print("🔹 Loading SER feature extractor...")
feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_DIR)

print("🔹 Loading SER model...")
model = HubertForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

print(f"✅ SER model loaded on {device}")


def predict_speech_emotion(audio_path: str) -> str:
    """
    Predict emotion from English speech audio.
    """
    if not os.path.exists(audio_path):
        return "audio_not_found"

    speech, _ = librosa.load(audio_path, sr=TARGET_SR, mono=True)

    if speech is None or len(speech) == 0:
        return "empty_audio"

    inputs = feature_extractor(
        [speech],
        sampling_rate=TARGET_SR,
        padding=True,
        return_attention_mask=True,
        return_tensors="pt"
    )

    input_values = inputs.input_values.to(device)
    attention_mask = inputs.attention_mask.to(device)

    with torch.no_grad():
        logits = model(
            input_values=input_values,
            attention_mask=attention_mask
        ).logits

    predicted_id = torch.argmax(logits, dim=-1).item()
    return model.config.id2label[predicted_id]
