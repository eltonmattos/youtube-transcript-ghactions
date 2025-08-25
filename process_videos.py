import os
import argparse
import requests
import logging
from notion_client import Client
import openai
import time

# Configurações de logging
logging.basicConfig(level=logging.INFO, format="INFO: %(message)s")

# Variáveis de ambiente
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")  # normal, não secret
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT", "Resuma o seguinte texto:")

# Inicializa OpenAI
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Inicializa Notion
notion = None
if NOTION_PARENT_ID:
    try:
        notion = Client(auth=os.getenv("NOTION_TOKEN"))
        logging.info("Notion configurado com sucesso")
    except Exception as e:
        logging.error(f"Erro ao configurar Notion: {e}")

SUPADATA_TRANSCRIPT_ENDPOINT = "https://api.supadata.ai/v1/transcript"
SUPADATA_PLAYLIST_ENDPOINT = "https://api.supadata.ai/v1/youtube/playlist"
MAX_BLOCK_SIZE = 2000

# -------- Funções --------

def fetch_transcript(video_url):
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": video_url, "text": False}
    try:
        resp = requests.get(SUPADATA_TRANSCRIPT_ENDPOINT, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if 'content' in data:
            content = data['content']
            if isinstance(content, list):
                return ' '.join(segment.get('text', '') for segment in content)
            return content
        elif resp.status_code == 202:
            job_id = data.get("jobId")
            return check_transcript_status(job_id)
        else:
            return ""
    except Exception as e:
        logging.error(f"Erro ao obter transcrição de {video_url}: {e}")
        return ""

def check_transcript_status(job_id):
    headers = {"x-api-key": SUPADATA_API_KEY}
    while True:
        resp = requests.get(f"{SUPADATA_TRANSCRIPT_ENDPOINT}/{job_id}", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            if status == "completed":
                content = data.get("content", [])
                if isinstance(content, list):
                    return ' '.join(segment.get('text', '') for segment in content)
                return content
            elif status == "failed":
                logging.error("Transcrição falhou.")
                return ""
        time.sleep(5)

def fetch_playlist_videos(playlist_url):
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": playlist_url}
    try:
        resp = requests.get(SUPADATA_PLAYLIST_ENDPOINT, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        videos = [item.get("url") for item in data.get("videos", []) if item.get("url")]
        return videos
    except Exception as e:
        logging.error(f"Erro ao obter vídeos da playlist {playlist_url}: {e}")
        return []

def process_text_with_openai(text):
    if not OPENAI_API_KEY or not OPENAI_MODEL:
        logging.warning("OpenAI não configurado, retornando texto original")
        return text

    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": f"{OPENAI_PROMPT}\n{text}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Erro no OpenAI: {e}")
        return text

def dividir_em_blocos(texto):
    paragrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    blocos = []
    bloco_atual = ""

    for p in paragrafos:
        if len(bloco_atual) + len(p) + 1 <= MAX_BLOCK_SIZE:
            bloco_atual = f"{bloco_atual}\n{p}" if bloco_atual else p
        else:
            if bloco_atual:
                blocos.append(bloco_atual)
            while len(p) > MAX_BLOCK_SIZE:
                blocos.append(p[:MAX_BLOCK_SIZE])
                p = p[MAX_BLOCK_SIZE:]
            bloco_atual = p

    if bloco_atual:
        blocos.append(bloco_atual)

    return blocos

def create_notion_page(title, texto):
    if not notion:
        logging.warning("Notion não configurado, pulando página")
        return

    blocos = dividir_em_blocos(texto)
    children = [
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": b}}]}}
        for b in blocos
    ]

    try:
        notion.pages.create(
            parent={"type": "page_id", "page_id": NOTION_PARENT_ID},
            properties={"title": [{"type": "text", "text": {"content": title}}]},
            children=children
        )
        logging.info(f"Página '{title}' criada no Notion ({len(blocos)} blocos)")
    except Exception as e:
        logging.error(f"Erro ao criar página no Notion: {e}")

# -------- Main --------

def main():
    parser = argparse.ArgumentParser(description="Process YouTube transcripts via Supadata")
    parser.add_argument("--videos", nargs="+", help="URLs ou IDs de vídeos do YouTube")
    parser.add_argument("--playlist", help="URL de uma playlist do YouTube")
    args = parser.parse_args()

    video_urls = []

    if args.videos:
        for vid in args.videos:
            if vid.startswith("http"):
                video_urls.append(vid)
            else:
                video_urls.append(f"https://www.youtube.com/watch?v={vid}")

    if args.playlist:
        video_urls.extend(fetch_playlist_videos(args.playlist))

    if not video_urls:
        logging.warning("Nenhum vídeo fornecido")
        return

    for video_url in video_urls:
        logging.info(f"Processando vídeo {video_url}...")
        transcript = fetch_transcript(video_url)
        if not transcript:
            continue
        logging.info(f"Transcrição obtida ({len(transcript)} caracteres)")

        processed_text = process_text_with_openai(transcript)
        logging.info(f"Texto processado ({len(processed_text)} caracteres)")

        create_notion_page(f"Transcrição {video_url.split('=')[-1]}", processed_text)

if __name__ == "__main__":
    main()
