import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")

def create_page(title: str, blocks: list[str]) -> None:
    """
    Cria uma página filha dentro de outra página no Notion com título e blocos de texto.

    Observações:
    - Não se deve usar `properties` com `title` para páginas filhas.
    - O título é criado como o primeiro bloco do tipo `heading_1`.
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Primeiro bloco será o título
    children = [{
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": title}}]
        }
    }]

    # Adiciona o restante dos blocos como parágrafos
    for block in blocks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": block}}]}
        })

    payload = {
        "parent": {"page_id": NOTION_PARENT_ID},  # página existente
        "children": children
    }

    response = requests.post(url, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Erro ao criar página no Notion:", e)
        print("Response:", response.text)
        raise
