import os
import argparse
import logging
import requests
import time
from notion_client import Client
from openai import OpenAI

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Variáveis de ambiente
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # pode ser sobrescrito pelo secret
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT", "Resuma o seguinte texto:")  # secret opcional

if not SUPADATA_API_KEY:
    logging.warning("SUPADATA_API_KEY não configurada, transcrições não funcionarão.")
if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY não configurada, resumos serão pulados.")
if not NOTION_TOKEN or not NOTION_PARENT_ID:
    logging.warning("Notion não configurado, páginas não serão criadas.")

# Inicializa cliente Notion
notion = None
if NOTION_TOKEN and NOTION_PARENT_ID:
    try:
        notion = Client(auth=NOTION_TOKEN)
        logging.info("Notion configurado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao configurar Notion: {e}")

# Inicializa cliente OpenAI
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

SUPADATA_PLAYLIST_ENDPOINT = "https://api.supadata.ai/v1/youtube/playlist"

# ---------------- Supadata: Transcrição ----------------

def verificar_status_transcricao(job_id, api_key):
    headers = {'x-api-key': api_key}
    while True:
        response = requests.get(f'https://api.supadata.ai/v1/transcript/{job_id}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            if status == 'completed':
                content = data.get('content', [])
                if isinstance(content, list):
                    return ' '.join(segment.get('text', '') for segment in content)
                return content
            elif status == 'failed':
                return "Erro: Processamento falhou."
        time.sleep(5)

def fetch_transcript(video_url):
    headers = {'x-api-key': SUPADATA_API_KEY}
    params = {'url': video_url, 'text': False}
    
    try:
        response = requests.get('https://api.supadata.ai/v1/transcript', headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            content = data.get('content')
            if isinstance(content, list):
                return ' '.join(segment.get('text', '') for segment in content)
            return content
        elif response.status_code == 202:
            job_id = response.json().get('jobId')
            return verificar_status_transcricao(job_id, SUPADATA_API_KEY)
        else:
            logging.error(f"Erro Supadata: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Erro ao obter transcrição: {e}")
        return None

# ---------------- Playlist ----------------

def fetch_playlist_videos(playlist_url):
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": playlist_url}
    try:
        resp = requests.get(SUPADATA_PLAYLIST_ENDPOINT, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        videos = [item.get("url") for item in data.get("videos", []) if item.get("url")]
        if not videos:
            logging.warning(f"Nenhum vídeo retornado para playlist {playlist_url}")
        return videos
    except Exception as e:
        logging.error(f"Erro ao obter vídeos da playlist {playlist_url}: {e}")
        return []

# ---------------- Resumo OpenAI ----------------

def summarize_text(text, chunk_size=3000):
    if not client:
        return None
    summaries = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": f"{OPENAI_PROMPT}\n{chunk}"}]
            )
            summaries.append(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Erro no OpenAI: {e}")
    return "\n".join(summaries)

# ---------------- Notion ----------------

def create_notion_page(title, content):
    if not notion:
        logging.warning("Notion não configurado, pulando criação de página.")
        return
    try:
        notion.pages.create(
            parent={"type": "page_id", "page_id": NOTION_PARENT_ID},
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            children=[{
                "object": "block",
                "type": "paragraph",
                "paragraph": {"text": [{"type": "text", "text": {"content": content}}]}
            }]
        )
        logging.info(f"Página '{title}' criada no Notion.")
    except Exception as e:
        logging.error(f"Erro ao criar página no Notion: {e}")

# ---------------- Main ----------------

def main():
    parser = argparse.ArgumentParser(description="Obter transcrições e resumos via Supadata")
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

        summary = summarize_text(transcript) or "Resumo não disponível"
        logging.info(f"Resumo gerado ({len(summary)} caracteres)")

        md_content = f"# Transcrição\n\n{transcript}\n\n---\n\n# Resumo\n\n{summary}"
        create_notion_page(f"Transcrição {video_url.split('=')[-1]}", md_content)

if __name__ == "__main__":
    main()
