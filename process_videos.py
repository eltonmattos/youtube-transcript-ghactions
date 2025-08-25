import os
import argparse
import requests
from notion_client import Client
import openai

# Configurações
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa cliente Notion
notion = Client(auth=NOTION_TOKEN) if NOTION_TOKEN else None

SUPADATA_TRANSCRIPT_ENDPOINT = "https://api.supadata.ai/v1/youtube/transcript"
SUPADATA_PLAYLIST_ENDPOINT = "https://api.supadata.ai/v1/youtube/playlist"

def fetch_transcript(video_url):
    """Obtém a transcrição de um vídeo via Supadata"""
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": video_url}
    try:
        resp = requests.get(SUPADATA_TRANSCRIPT_ENDPOINT, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("transcript")
    except Exception as e:
        print(f"Erro ao obter transcrição de {video_url}: {e}")
        return None

def fetch_playlist_videos(playlist_url):
    """Obtém lista de vídeos de uma playlist via Supadata"""
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": playlist_url}
    try:
        resp = requests.get(SUPADATA_PLAYLIST_ENDPOINT, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Retorna lista de URLs ou IDs
        return [item.get("url") for item in data.get("videos", []) if item.get("url")]
    except Exception as e:
        print(f"Erro ao obter vídeos da playlist {playlist_url}: {e}")
        return []

def summarize_text(text):
    """Gera resumo usando OpenAI"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Resuma o seguinte texto:\n{text}"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erro no OpenAI: {e}")
        return None

def create_notion_page(title, content):
    """Cria página no Notion"""
    if not notion:
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
        print(f"Página '{title}' criada no Notion ✅")
    except Exception as e:
        print(f"Erro ao criar página no Notion: {e}")

def main():
    parser = argparse.ArgumentParser(description="Obter transcrições e resumos via Supadata")
    parser.add_argument("--videos", nargs="+", help="URLs ou IDs de vídeos do YouTube")
    parser.add_argument("--playlist", help="URL de uma playlist do YouTube")
    args = parser.parse_args()

    video_urls = []

    # Adiciona vídeos individuais
    if args.videos:
        for vid in args.videos:
            if vid.startswith("http"):
                video_urls.append(vid)
            else:
                video_urls.append(f"https://www.youtube.com/watch?v={vid}")

    # Extrai vídeos da playlist
    if args.playlist:
        playlist_videos = fetch_playlist_videos(args.playlist)
        video_urls.extend(playlist_videos)

    if not video_urls:
        print("Nenhum vídeo fornecido")
        return

    for video_url in video_urls:
        print(f"\n📺 Processando vídeo {video_url}...")
        transcript = fetch_transcript(video_url)
        if not transcript:
            continue

        summary = summarize_text(transcript) or "Resumo não disponível"
        md_content = f"# Transcrição\n\n{transcript}\n\n---\n\n# Resumo\n\n{summary}"
        create_notion_page(f"Transcrição {video_url.split('=')[-1]}", md_content)

if __name__ == "__main__":
    main()
