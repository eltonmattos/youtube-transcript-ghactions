# -*- coding: utf-8 -*-
import os
import requests
import time

# Variáveis de ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def process_text(transcript: str, prompt: str, model: str) -> str:
    """
    Processa o texto usando o modelo especificado.
    - Se for Gemini (model começa com "gemini"), usa Gemini API
    - Se for OpenAI (model começa com "gpt"), usa OpenAI API
    """
    print("DEBUG AI_MODEL:", model)
    
    if model.lower().startswith("gemini"):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não está definida!")
        print("DEBUG GEMINI_API_KEY length:", len(GEMINI_API_KEY))
        return process_with_gemini(transcript, prompt, model)
    
    elif model.lower().startswith("gpt"):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não está definida!")
        print("DEBUG OPENAI_API_KEY length:", len(OPENAI_API_KEY))
        return process_with_openai(transcript, prompt, model)
    
    else:
        raise ValueError(f"Modelo desconhecido: {model}")


# ---------------- GEMINI ----------------

def process_with_gemini(transcript: str, prompt: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "X-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {"parts": [{"text": f"{prompt}\n\n{transcript}"}]}
        ]
    }

    max_retries = 5
    backoff = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 401:
                raise ValueError("401 Unauthorized: verifique GEMINI_API_KEY")
            elif response.status_code == 429:
                print(f"429 Too Many Requests, retry em {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except requests.exceptions.RequestException as e:
            print(f"Erro Gemini: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff)
            backoff *= 2


# ---------------- OPENAI ----------------

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

    max_retries = 5
    backoff = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 401:
                raise ValueError("401 Unauthorized: verifique OPENAI_API_KEY")
            elif response.status_code == 429:
                print(f"429 Too Many Requests, retry em {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"Erro OpenAI: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff)
            backoff *= 2
