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

def process_with_gemini(transcript: str, prompt: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{prompt}\n\n{transcript}"}]}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error {e.response.status_code}: {e.response.text}")
        raise
    return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


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
