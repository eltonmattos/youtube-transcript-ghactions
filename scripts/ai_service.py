import os
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def process_text(transcript: str, prompt: str, model: str) -> str:
    """Processa texto com base no modelo escolhido"""
    if model.startswith("gpt"):
        return process_with_openai(transcript, prompt, model)
    elif model.startswith("gemini"):
        return process_with_gemini(transcript, prompt, model)
    else:
        raise ValueError(f"Model {model} not supported")

def process_with_openai(transcript: str, prompt: str, model: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcript}
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def process_with_gemini(transcript: str, prompt: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{prompt}\n\n{transcript}"}]}
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
