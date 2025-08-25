import os
import sys
import time
import logging
import requests
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format="INFO: %(message)s")


# ---------- SUPADATA ----------
def get_transcript_supadata(video_url: str):
    """
    Obtém transcrição e título do vídeo via Supadata.
    Retorna (transcrição, título).
    """
    SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
    headers = {"Authorization": f"Bearer {SUPADATA_API_KEY}"}
    url = f"https://api.supadata.ai/transcript?url={video_url}"

    logging.info(f"Processando vídeo {video_url}...")

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        logging.error(f"Erro Supadata: {resp.text}")
        return None, None

    data = resp.json()
    transcript = data.get("text", "")
    title = data.get("title", "Transcrição sem título")

    logging.info(f"Transcrição obtida ({len(transcript)} caracteres), título='{title}'")
    return transcript, title


# ---------- AI PROCESSING ----------
def call_openai(model: str, prompt: str, text: str) -> Optional[str]:
    import openai

    openai.api_key = os.getenv("OPENAI_API_KEY")

    retries = 3
    for attempt in range(retries):
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.warning(f"Tentativa {attempt+1}/{retries} falhou: {e}")
            time.sleep(2 ** attempt)
    return None


def call_gemini(model: str, prompt: str, text: str) -> Optional[str]:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    retries = 3
    for attempt in range(retries):
        try:
            model_gen = genai.GenerativeModel(model)
            response = model_gen.generate_content(f"{prompt}\n\n{text}")
            return response.text
        except Exception as e:
            logging.warning(f"Tentativa {attempt+1}/{retries} falhou: {e}")
            time.sleep(2 ** attempt)
    return None


def process_with_ai(transcript: str, ai_model: str, ai_prompt: str) -> str:
    if not ai_model:
        logging.warning("AI_MODEL não configurado. Retornando texto original.")
        return transcript

    logging.info(f"Usando modelo AI: '{ai_model}'")

    if ai_model.startswith("gpt"):
        result = call_openai(ai_model, ai_prompt, transcript)
    elif ai_model.startswith("gemini"):
        result = call_gemini(ai_model, ai_prompt, transcript)
    else:
        logging.error(f"Modelo não suportado: {ai_model}")
        return transcript

    if result:
        logging.info(f"Texto processado ({len(result)} caracteres)")
        return result
    else:
        logging.error("Falha no processamento AI, retornando transcrição bruta")
        return transcript


# ---------- NOTION ----------
def split_into_blocks(text: str, max_len: int = 2000) -> List[str]:
    paragraphs = text.split("\n")
    blocks, current = [], ""

    for p in paragraphs:
        if len(current) + len(p) + 1 <= max_len:
            current += ("\n" if current else "") + p
        else:
            blocks.append(current)
            current = p
    if current:
        blocks.append(current)

    return blocks


def create_notion_page(title: str, content: str, parent_id: str):
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        logging.error("NOTION_TOKEN não configurado")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    blocks = split_into_blocks(content)

    children = []
    for block in blocks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": block[:2000]}}],
            },
        })

    data = {
        "parent": {"database_id": parent_id},
        "properties": {
            "title": [
                {"type": "text", "text": {"content": title}}
            ]
        },
        "children": children,
    }

    resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    if resp.status_code != 200:
        logging.error(f"Erro ao criar página no Notion: {resp.text}")
    else:
        logging.info(f"Página '{title}' criada no Notion ({len(blocks)} blocos)")


# ---------- MAIN ----------
def main():
    notion_parent_id = os.getenv("NOTION_PARENT_ID")
    ai_model = os.getenv("AI_MODEL")
    ai_prompt = os.getenv("AI_PROMPT", "Resuma o seguinte texto:")

    if not notion_parent_id:
        logging.error("NOTION_PARENT_ID não configurado")
        return

    logging.info("Notion configurado com sucesso")

    video_urls = sys.argv[1:]
    if not video_urls:
        logging.error("Nenhum vídeo fornecido")
        return

    for url in video_urls:
        transcript, title = get_transcript_supadata(url)
        if not transcript:
            continue

        processed_text = process_with_ai(transcript, ai_model, ai_prompt)
        create_notion_page(title, processed_text, notion_parent_id)


if __name__ == "__main__":
    main()
