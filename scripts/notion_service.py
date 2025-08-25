# -*- coding: utf-8 -*-
import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
NOTION_API_URL = "https://api.notion.com/v1/blocks"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


def split_text_blocks(text: str, max_len: int = 2000) -> list[str]:
    """
    Divide o texto em blocos de no máximo max_len caracteres,
    tentando respeitar parágrafos.
    """
    blocks = []
    paragraphs = text.split("\n\n")  # considera parágrafos gerados pela IA
    current_block = ""

    for p in paragraphs:
        if len(current_block) + len(p) + 2 <= max_len:
            if current_block:
                current_block += "\n\n" + p
            else:
                current_block = p
        else:
            if current_block:
                blocks.append(current_block)
            # Se o parágrafo sozinho for maior que max_len, divide dentro do parágrafo
            while len(p) > max_len:
                blocks.append(p[:max_len])
                p = p[max_len:]
            current_block = p
    if current_block:
        blocks.append(current_block)
    return blocks


def create_notion_block(parent_id: str, text: str):
    """
    Cria um único bloco de texto no Notion.
    """
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "object": "block",
        "type": "paragraph",
        "paragraph": {"text": [{"type": "text", "text": {"content": text}}]}
    }
    response = requests.post(f"{NOTION_API_URL}/{parent_id}/children", headers=HEADERS, json=payload)
    response.raise_for_status()


def create_notion_page(title: str, text: str):
    """
    Cria uma página no Notion, dividindo o texto em blocos de 2000 caracteres.
    """
    # Primeiro cria a página
    payload = {
        "parent": {"database_id": NOTION_PARENT_ID},
        "properties": {
            "title": {
                "title": [
                    {"text": {"content": title}}
                ]
            }
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    response.raise_for_status()
    page_id = response.json()["id"]

    # Divide o texto em blocos e cria cada bloco
    for block_text in split_text_blocks(text, max_len=2000):
        create_notion_block(page_id, block_text)

    return page_id
