import os
import argparse
import requests
import time
from notion_client import Client
from bs4 import BeautifulSoup

# Dependendo do AI_MODEL, usa OpenAI ou Gemini
import openai
try:
    import google.generativeai as gemini
except ImportError:
    gemini = None

# Configurações
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")  # não secret
AI_MODEL = os.getenv("AI_MODEL")
AI_PROMPT = os.getenv("AI_PROMPT") or "Resuma o seguinte texto:"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializa Notion
notion = None
if NOTION_TOKEN and NOTION_PARENT_ID:
    try:
        notion = Client(auth=NOTION_TOKEN)
        print(f"INFO: Notion configurado com sucesso")
    except Exception as e:
        print(f"ERROR: Erro ao configurar Notion: {e}")

# Configura OpenAI/Gemini
if AI_MODEL.startswith("gpt") and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
elif AI_MODEL.startswith("gemini") and GEMINI_API_KEY and gemini:
    gemini.configure(api_key=GEMINI_API_KEY)

# --- Funções ---
def fetch_transcript(video_url):
    """Obtem a transcrição via SupaData (text=False)"""
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": video_url, "text": False}
    try:
        resp = requests.get("https://api.supadata.ai/v1/youtube/transcript", headers=headers, params=params, timeout=60)
        if resp.status_code == 202:
            # Job async
            job_id = resp.json().get("jobId")
            return wait_transcript_job(job_id)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content")
        if isinstance(content, list):
            return " ".join(seg.get("text", "") for seg in content)
        elif isinstance(content, str):
            return content
        return ""
    except Exception as e:
        print(f"ERROR: Falha ao processar vídeo {video_url}: {e}")
        return None

def wait_transcript_job(job_id):
    headers = {"x-api-key": SUPADATA_API_KEY}
    while True:
        resp = requests.get(f"https://api.supadata.ai/v1/transcript/{job_id}", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            if status == "completed":
                content = data.get("content", [])
                return " ".join(seg.get("text", "") for seg in content) if isinstance(content, list) else content
            elif status == "failed":
                return None
        time.sleep(5)

def fetch_playlist_videos(playlist_url):
    """Obtém vídeos de uma playlist via SupaData"""
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": playlist_url}
    try:
        resp = requests.get("https://api.supadata.ai/v1/youtube/playlist", headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return [v.get("url") for v in data.get("videos", []) if v.get("url")]
    except Exception as e:
        print(f"ERROR: Falha ao obter vídeos da playlist {playlist_url}: {e}")
        return []

def get_video_title(video_url):
    """Pega o título do vídeo via scraping (sem usar cota da SupaData)"""
    try:
        resp = requests.get(video_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.replace(" - YouTube", "").strip()
        return title
    except Exception as e:
        print(f"ERROR: Não foi possível obter título: {e}")
        return video_url.split("v=")[-1]

def process_with_ai(text):
    """Envia texto ao modelo definido por AI_MODEL"""
    if not text:
        return ""
    if AI_MODEL.startswith("gpt") and openai.api_key:
        try:
            resp = openai.ChatCompletion.create(
                model=AI_MODEL,
                messages=[{"role": "user", "content": AI_PROMPT + "\n" + text}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"ERROR: OpenAI: {e}")
            return text
    elif AI_MODEL.startswith("gemini") and GEMINI_API_KEY and gemini:
        try:
            return gemini.chat(messages=[{"author": "user", "content": AI_PROMPT + "\n" + text}]).last
        except Exception as e:
            print(f"ERROR: Gemini: {e}")
            return text
    else:
        return text  # fallback

def split_paragraphs(text, max_len=2000):
    """Divide texto em parágrafos e em blocos ≤ max_len"""
    paras = text.split("\n")
    blocks = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        while len(p) > max_len:
            blocks.append(p[:max_len])
            p = p[max_len:]
        blocks.append(p)
    return blocks

def create_notion_page(title, text):
    if not notion:
        print("WARNING: Notion não configurado, pulando")
        return
    blocks = split_paragraphs(text)
    children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": b}}]}} for b in blocks]
    try:
        notion.pages.create(
            parent={"page_id": NOTION_PARENT_ID},
            properties={"title": [{"type": "text", "text": {"content": title}}]},
            children=children
        )
        print(f"INFO: Página '{title}' criada no Notion ({len(blocks)} blocos)")
    except Exception as e:
        print(f"ERROR: Falha ao criar página no Notion: {e}")

# --- Main ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", help="URLs ou IDs de vídeos/playlist")
    args = parser.parse_args()

    video_urls = []

    # Separar vídeos de playlists
    for vid in args.videos:
        if "playlist" in vid:
            video_urls.extend(fetch_playlist_videos(vid))
        elif vid.startswith("http"):
            video_urls.append(vid)
        else:
            video_urls.append(f"https://www.youtube.com/watch?v={vid}")

    if not video_urls:
        print("WARNING: Nenhum vídeo para processar")
        return

    for video_url in video_urls:
        print(f"INFO: Processando vídeo {video_url}...")
        title = get_video_title(video_url)
        transcript = fetch_transcript(video_url)
        if not transcript:
            print(f"ERROR: Transcrição não disponível para {video_url}")
            continue
        processed_text = process_with_ai(transcript)
        create_notion_page(title, processed_text)

if __name__ == "__main__":
    main()
