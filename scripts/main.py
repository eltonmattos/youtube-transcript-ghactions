import os
import sys
from youtube_service import get_video_data
from ai_service import process_text
from notion_service import create_page

def split_into_blocks(text: str, max_len: int = 2000) -> list[str]:
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def run_pipeline(video_urls: list[str]):
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
    # Recebe lista de URLs como argumento separado por vírgula
    if len(sys.argv) < 2:
        print("Por favor, passe a lista de URLs de vídeos como argumento.")
        sys.exit(1)

    urls_input = sys.argv[1]
    urls = [url.strip() for url in urls_input.split(",") if url.strip()]
    run_pipeline(urls)
