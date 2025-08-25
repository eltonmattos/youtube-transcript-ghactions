import os
import argparse
import requests
from yt_dlp import YoutubeDL
import openai
from notion_client import Client

# Configurações Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")

# Configura OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa cliente Notion
notion = Client(auth=NOTION_TOKEN)

def download_transcript(video_url):
    """
    Baixa transcrição priorizando:
    1) Legenda manual pt-BR
    2) Legenda automática pt-BR
    Retorna texto simples
    """
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'subtitlesformat': 'vtt',
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        # Legenda manual pt-BR
        subs = info.get('subtitles') or {}
        if 'pt-BR' in subs:
            url = subs['pt-BR'][0]['url']
            return clean_vtt(requests.get(url).text)

        # Legenda automática pt-BR
        auto_subs = info.get('automatic_captions') or {}
        if 'pt-BR' in auto_subs:
            url = auto_subs['pt-BR'][0]['url']
            return clean_vtt(requests.get(url).text)

    return None

def clean_vtt(vtt_text):
    """Converte VTT em texto simples removendo timestamps"""
    lines = vtt_text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or '-->' in line:
            continue
        clean_lines.append(line)
    return " ".join(clean_lines)

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

    # Se passou playlist
    if args.playlist:
        ydl_opts = {'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(args.playlist, download=False)
            video_list.extend([entry['webpage_url'] for entry in info['entries']])

    # Se passou lista de vídeos
    if args.videos:
        video_list.extend(args.videos)

    if not video_list:
        print("Nenhum vídeo fornecido")
        return

    for vid_url in video_list:
        print(f"\n📺 Processando vídeo {vid_url}...")
        transcript = download_transcript(vid_url)
        if not transcript:
            print(f"Transcrição não encontrada para {vid_url}")
            continue

        summary = process_with_openai(transcript) or "Resumo não disponível"
        md_content = f"# Transcrição\n\n{transcript}\n\n---\n\n# Resumo\n\n{summary}"
        create_notion_page(f"Transcrição {vid_url}", md_content)

if __name__ == "__main__":
    main()
