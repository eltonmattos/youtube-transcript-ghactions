import os
import argparse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import openai
from notion_client import Client

# Configurações Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")

# Configura OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa cliente Notion
notion = Client(auth=NOTION_TOKEN)

def download_transcript(video_id):
    """
    Baixa transcrição usando youtube-transcript-api
    Prioriza pt-BR, depois pt
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['pt-BR', 'pt'])
        text = " ".join([t['text'] for t in transcript.fetch()])
        return text
    except TranscriptsDisabled:
        print(f"Transcrição desativada para {video_id}")
    except NoTranscriptFound:
        print(f"Nenhuma transcrição disponível para {video_id}")
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
    """Cria página no Notion com título e conteúdo em Markdown"""
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
    parser.add_argument("--videos", nargs="+", help="IDs ou URLs de vídeos do YouTube")
    args = parser.parse_args()

    video_list = []

    # Se passou lista de vídeos
    if args.videos:
        video_list.extend(args.videos)

    if not video_list:
        print("Nenhum vídeo fornecido")
        return

    for vid_url in video_list:
        # Extrair o ID caso seja URL
        if "youtube.com/watch" in vid_url or "youtu.be/" in vid_url:
            import re
            match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", vid_url)
            if match:
                video_id = match.group(1)
            else:
                print(f"ID não encontrado em {vid_url}")
                continue
        else:
            video_id = vid_url

        print(f"\n📺 Processando vídeo {video_id}...")
        transcript = download_transcript(video_id)
        if not transcript:
            continue

        summary = process_with_openai(transcript) or "Resumo não disponível"
        md_content = f"# Transcrição\n\n{transcript}\n\n---\n\n# Resumo\n\n{summary}"
        create_notion_page(f"Transcrição {video_id}", md_content)

if __name__ == "__main__":
    main()
