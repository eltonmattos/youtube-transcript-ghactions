import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")

def create_page(title: str, blocks: list[str]) -> None:
    """Cria pagina no Notion com titulo e blocos de texto"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    children = []
    for block in blocks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": block}}]}
        })

    payload = {
        "parent": {"type": "page_id", "page_id": NOTION_PARENT_ID},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        "children": children
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
