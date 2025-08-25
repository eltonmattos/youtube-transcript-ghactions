import os
import argparse
import requests
import time
import random
import logging
from notion_client import Client
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ----------------------------
# Configurações / Variáveis
# ----------------------------
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT", "")

# ----------------------------
# Inicializa clientes
# ----------------------------
notion = None
if NOTION_TOKEN and NOTION_PARENT_ID:
    try:
        notion = Client(auth=NOTION_TOKEN)
        logging.info("Notion configurado com sucesso")
    except Exception as e:
        logging.warning(f"Erro ao configurar Notion: {e}")

client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Logging das variáveis não secret
# ----------------------------
logging.info(f"NOTION_PARENT_ID='{NOTION_PARENT_ID}'")
logging.info(f"OPENAI_MODEL='{OPENAI_MODEL}'")
logging.info(f"OPENAI_PROMPT='{OPENAI_PROMPT}'")

# ----------------------------
# Funções Supadata
# ----------------------------
def verificar_status_transcricao(job_id, api_key):
    headers = {"x-api-key": api_key}
    while True:
        response = requests.get(f'https://api.supadata.ai/v1/transcript/{job_id}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status == "completed":
                content = data.get("content", [])
                if isinstance(content, list):
                    return " ".join(segment.get("text", "") for segment in content)
                return content
            elif status == "failed":
                return "Erro: Processamento falhou."
        time.sleep(5)

def fetch_transcript(video_url):
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": video_url, "text": False}
    try:
        resp = requests.get("https://api.supadata.ai/v1/transcript", headers=headers, params=params, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", [])
            if isinstance(content, list):
                return " ".join(segment.get("text", "") for segment in content)
            return content
        elif resp.status_code == 202:
            job_id = resp.json().get("jobId")
            return verificar_status_transcricao(job_id, SUPADATA_API_KEY)
        else:
            logging.error(f"Erro Supadata {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        logging.error(f"Erro ao obter transcrição de {video_url}: {e}")
        return None

def fetch_playlist_videos(playlist_url):
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": playlist_url}
    try:
        resp = requests.get("https://api.supadata.ai/v1/youtube/playlist", headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        videos = [item.get("url") for item in data.get("videos", []) if item.get("url")]
        if not videos:
            logging.warning(f"Nenhum vídeo retornado para playlist {playlist_url}")
        return videos
    except Exception as e:
        logging.error(f"Erro ao obter vídeos da playlist {playlist_url}: {e}")
        return []

# ----------------------------
# Função de envio para IA
# ----------------------------
def process_text_with_ai(text, chunk_size=3000):
    """
    Envia o texto ao modelo OpenAI e retorna a resposta completa.
    """
    if not client:
        logging.warning("OpenAI não configurado, retornando texto original")
        return text

    model = OPENAI_MODEL.strip() if OPENAI_MODEL else None
    if not model:
        logging.error("OPENAI_MODEL não definido corretamente, retornando texto original")
        return text

    logging.info(f"Usando modelo OpenAI: '{model}'")

    def call_ai(chunk):
        retries = 3
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"{OPENAI_PROMPT}\n{chunk}"}]
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e):
                    wait = (2 ** attempt) + random.random()
                    logging.warning(f"429 Too Many Requests. Tentando novamente em {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    logging.error(f"Erro no OpenAI: {e}")
                    return chunk
        logging.error("Falha após várias tentativas, retornando chunk original")
        return chunk

    if len(text) <= chunk_size:
        return call_ai(text)

    processed_chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        processed_chunks.append(call_ai(chunk))

    return "\n".join(processed_chunks)

# ----------------------------
# Função Notion
# ----------------------------
def create_notion_page(title, content):
    if not notion:
        logging.warning("Notion não configurado, pulando criação de página")
        return
    try:
        notion.pages.create(
            parent={"type": "page_id", "page_id": NOTION_PARENT_ID},
            properties={"title": [{"type": "text", "text": {"content": title}}]},
            children=[{
                "object": "block",
                "type": "paragraph",
                "paragraph": {"text": [{"type": "text", "text": {"content": content}}]}
            }]
        )
        logging.info(f"Página '{title}' criada no Notion")
    except Exception as e:
        logging.error(f"Erro ao criar página no Notion: {e}")

# ----------------------------
# Main
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Processar vídeos do YouTube via Supadata")
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
        playlist_videos = fetch_playlist_videos(args.playlist)
        video_urls.extend(playlist_videos)

    if not video_urls:
        logging.warning("Nenhum vídeo fornecido para processar")
        return

    for video_url in video_urls:
        logging.info(f"Processando vídeo {video_url}...")
        transcript = fetch_transcript(video_url)
        if not transcript:
            continue
        logging.info(f"Transcrição obtida ({len(transcript)} caracteres)")

        processed_text = process_text_with_ai(transcript)
        logging.info(f"Texto processado ({len(processed_text)} caracteres)")

        create_notion_page(f"Transcrição {video_url.split('=')[-1]}", processed_text)

if __name__ == "__main__":
    main()
