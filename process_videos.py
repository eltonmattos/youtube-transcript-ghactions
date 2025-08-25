import os
import argparse
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Playlist
import openai
from notion_client import Client

# Configurações Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")           # Token da integração
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")   # ID da página ou database

# Configura OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa cliente Notion
notion = Client(auth=NOTION_TOKEN)

def download_transcript(video_id):
    """Baixa a transcrição do vídeo pelo ID usando a nova API"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Tenta encontrar transcrição em português ou inglês
        transcript = transcript_list.find_transcript(['pt', 'en'])
        # Busca o conteúdo
        text = " ".join([t["text"] for t in transcript.fetch()])
        return text
    except Exception as e:
        print(f"Erro ao baixar transcrição de {video_id}: {e}")
        return None

def process_with_openai(text):
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
    """Cria uma página no Notion com título e conteúdo em Markdown"""
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
    parser = argparse.ArgumentParser(description="Baixar transcrições e enviar ao Notion")
    parser.add_argument("--playlist", type=str, help="URL da playlist do YouTube")
    parser.add_argument("--videos", nargs="+", help="IDs de vídeos do YouTube separados por espaço")
    args = parser.parse_args()

    video_ids = []

    # Coleta vídeos da playlist
    if args.playlist:
        try:
            p = Playlist(args.playlist)
            video_ids.extend([v.video_id for v in p.videos])
        except Exception as e:
            print(f"Erro ao carregar playlist: {e}")

    # Coleta vídeos passados manualmente
    if args.videos:
        video_ids.extend(args.videos)

    if not video_ids:
        print("Nenhum vídeo fornecido")
        return

    for vid in video_ids:
        print(f"\n📺 Processando vídeo {vid}...")
        text = download_transcript(vid)
        if not text:
            continue

        summary = process_with_openai(text) or "Resumo não disponível"
        md_content = f"# Transcrição do vídeo {vid}\n\n{text}\n\n---\n\n# Resumo\n\n{summary}"

        create_notion_page(f"Transcrição {vid}", md_content)

if __name__ == "__main__":
    main()
