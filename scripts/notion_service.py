import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")

def create_page(title: str, video_url: str, transcript_blocks: list[str]) -> None:
    """
    Cria uma página no Notion com:
    - Título oficial no campo `properties.title`
    - Embed do vídeo logo abaixo do título
    - Transcrição em blocos de parágrafo
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Blocos da página: primeiro embed, depois transcrição
    children = [{
        "object": "block",
        "type": "embed",
        "embed": {"url": video_url}
    }]

    for block in transcript_blocks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": block}}]}
        })

    payload = {
        "parent": {"page_id": NOTION_PARENT_ID},
        "properties": {
            "title": [{
                "type": "text",
                "text": {"content": title}
            }]
        },
        "children": children
    }

    response = requests.post(url, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Erro ao criar página no Notion:", e)
        print("Response:", response.text)
        raise
