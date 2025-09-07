# -*- coding: utf-8 -*-
import os
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pytube import Playlist
from youtube_service import get_video_data
from ai_service import process_text
from notion_service import create_page

def split_into_blocks(text: str, max_len: int = 2000) -> list[str]:
    """Divide o texto em blocos menores para não ultrapassar limites de API."""
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def normalize_video_url(url: str) -> str:
    """Normaliza links de vídeo:
    - Mantém apenas o parâmetro v= para vídeos normais.
    - Converte shorts para o formato watch?v=.
    - Remove parâmetros extras (list, t, etc.).
    """
    parsed = urlparse(url)

    # Caso seja link de shorts
    if "youtube.com/shorts/" in url:
        video_id = parsed.path.split("/")[-1]
        return f"https://www.youtube.com/watch?v={video_id}"

    # Caso seja link de vídeo padrão
    qs = parse_qs(parsed.query)
    if "v" in qs:
        clean_qs = {"v": qs["v"]}
        new_query = urlencode(clean_qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, "/watch", "", new_query, ""))

    # Se não bater com nenhum padrão conhecido, retorna como está
    return url

def expand_urls(urls: list[str]) -> list[str]:
    """Expande playlists em uma lista de vídeos e normaliza links individuais."""
    expanded = []
    for url in urls:
        url = url.strip()
        if not url:
            continue

        # Se for playlist explícita
        if "youtube.com/playlist" in url or ("list=" in url and "watch" not in url):
            print(f"Expandindo playlist: {url}")
            try:
                pl = Playlist(url)
                expanded.extend(pl.video_urls)
            except Exception as e:
                print(f"Erro ao processar playlist {url}: {e}")
        else:
            # Se for vídeo único (normal ou shorts), normaliza
            expanded.append(normalize_video_url(url))

    return expanded

def run_pipeline(video_urls: list[str]):
    """Executa o pipeline de download da transcrição, processamento e criação no Notion."""
    ai_model = os.getenv("AI_MODEL", "gpt-4o-mini")
    ai_prompt = os.getenv("AI_PROMPT", "Format the transcript into paragraphs with punctuation.")

    for url in video_urls:
        url = url.strip()
        if not url:
            continue
        print(f"Processing video: {url}")
        video_data = get_video_data(url)

        processed_text = process_text(
            video_data["transcript"],
            ai_prompt,
            ai_model
        )

        blocks = split_into_blocks(processed_text)
        title = f"{video_data['title']} - {video_data['channel']}"
        create_page(title, blocks)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Por favor, passe a lista de URLs de vídeos ou playlists como argumento.")
        sys.exit(1)

    urls_input = sys.argv[1]
    urls = [url.strip() for url in urls_input.split(",") if url.strip()]
    expanded_urls = expand_urls(urls)
    run_pipeline(expanded_urls)
