import os
import sys
import requests
from urllib.parse import urlparse, parse_qs

# Variáveis de ambiente
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
AI_MODEL = os.getenv("AI_MODEL")
AI_PROMPT = os.getenv("AI_PROMPT", "Process the following text:")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not NOTION_TOKEN or not NOTION_PARENT_ID:
    print("ERRO: NOTION_TOKEN e NOTION_PARENT_ID são obrigatórios")
    sys.exit(1)

if not AI_MODEL:
    print("ERRO: AI_MODEL não configurado")
    sys.exit(1)

# --------------------------
# Funções auxiliares
# --------------------------

def get_video_id(url):
    """Extrai o ID do vídeo do YouTube."""
    parsed_url = urlparse(url)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")
    return None


def get_video_title(video_id):
    """Obtém título do vídeo via oEmbed (não precisa de API key)."""
    try:
        resp = requests.get(f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json")
        if resp.status_code == 200:
            return resp.json().get("title", f"Vídeo {video_id}")
    except Exception:
        pass
    return f"Vídeo {video_id}"


def split_into_paragraphs(text, max_len=2000):
    """Divide texto em blocos ≤2000 chars preservando parágrafos."""
    paragraphs = []
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            continue
        while len(p) > max_len:
            paragraphs.append(p[:max_len])
            p = p[max_len:]
        paragraphs.append(p)
    return paragraphs


def send_to_ai(text):
    """Decide engine e processa texto."""
    if AI_MODEL.startswith("gpt-"):
        if not OPENAI_API_KEY:
            print("ERRO: OPENAI_API_KEY não configurado")
            return text
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        try:
            resp = client.chat.completions.create(
                model=AI_MODEL,
                messages=[{"role": "user", "content": f"{AI_PROMPT}\n{text}"}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"Erro OpenAI: {e}")
            return text

    elif AI_MODEL.startswith("gemini-"):
        if not GEMINI_API_KEY:
            print("ERRO: GEMINI_API_KEY não configurado")
            return text
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            model = genai.GenerativeModel(AI_MODEL)
            resp = model.generate_content(f"{AI_PROMPT}\n{text}")
            return resp.text
        except Exception as e:
            print(f"Erro Gemini: {e}")
            return text

    else:
        print(f"ERRO: Modelo '{AI_MODEL}' não suportado. Use 'gpt-*' ou 'gemini-*'")
        return text


def send_to_notion(video_title, paragraphs):
    """Cria página no Notion com blocos de texto."""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    children = []
    for p in paragraphs:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": p}}]
            }
        })

    data = {
        "parent": {"database_id": NOTION_PARENT_ID},
        "properties": {
            "title": [{"text": {"content": video_title}}]
        },
        "children": children
    }

    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 200:
        page_id = r.json().get("id")
        print(f"✅ Página '{video_title}' criada no Notion ({len(children)} blocos)")
        return page_id
    else:
        print("❌ Erro ao criar página no Notion:", r.text)
        return None


# --------------------------
# Fluxo principal
# --------------------------

def main(video_url, transcript_text):
    video_id = get_video_id(video_url)
    video_title = get_video_title(video_id)
    print(f"INFO: Processando vídeo '{video_title}'...")

    processed = send_to_ai(transcript_text)
    paragraphs = split_into_paragraphs(processed)
    send_to_notion(video_title, paragraphs)


if __name__ == "__main__":
    # Exemplo de uso: python script.py "<url>" "<texto>"
    if len(sys.argv) < 3:
        print("Uso: python script.py <youtube_url> <transcricao>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
