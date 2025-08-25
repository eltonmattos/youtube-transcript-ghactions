import os
import sys
import requests
import time
import openai
import google.generativeai as genai

# ==============================
# Configurações via variáveis
# ==============================
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_ID = os.getenv("NOTION_PARENT_ID")
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "").strip()
AI_PROMPT = os.getenv("AI_PROMPT", "Transforme o seguinte texto:")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not NOTION_TOKEN or not NOTION_PARENT_ID:
    print("ERROR: Variáveis do Notion não configuradas.")
    sys.exit(1)

if not SUPADATA_API_KEY:
    print("ERROR: SUPADATA_API_KEY não configurada.")
    sys.exit(1)

if not AI_MODEL:
    print("ERROR: AI_MODEL não configurada.")
    sys.exit(1)

print("INFO: Notion configurado com sucesso")
print(f"INFO: NOTION_PARENT_ID='{NOTION_PARENT_ID}'")
print(f"INFO: AI_MODEL='{AI_MODEL}'")
print(f"INFO: AI_PROMPT='{AI_PROMPT}'")

# ==============================
# Funções auxiliares
# ==============================

def get_playlist_videos(playlist_url: str):
    """Obtém lista de vídeos de uma playlist usando SupaData"""
    api_url = f"https://api.supadata.ai/playlist?url={playlist_url}"
    headers = {"Authorization": f"Bearer {SUPADATA_API_KEY}"}
    resp = requests.get(api_url, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return [item["url"] for item in data.get("videos", [])]


def get_video_transcript(video_url: str):
    """Obtém transcrição e título do vídeo"""
    api_url = f"https://api.supadata.ai/get-transcript?url={video_url}"
    headers = {"Authorization": f"Bearer {SUPADATA_API_KEY}"}
    resp = requests.get(api_url, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = " ".join([seg["text"] for seg in data.get("segments", [])])
    title = data.get("title", "Transcrição")
    return title, text


def split_paragraphs(text, max_len=2000):
    """Divide texto em blocos <= 2000 caracteres"""
    paragraphs = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            paragraphs.append(current.strip())
            current = line
        else:
            current += " " + line
    if current:
        paragraphs.append(current.strip())
    return paragraphs


def process_with_ai(text):
    """Envia texto para OpenAI ou Gemini"""
    if AI_MODEL.startswith("gpt"):
        if not OPENAI_API_KEY:
            print("WARNING: OPENAI_API_KEY não configurada, retornando texto original")
            return text
        openai.api_key = OPENAI_API_KEY
        try:
            response = openai.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": AI_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"ERROR: Erro no OpenAI: {e}")
            return text

    elif AI_MODEL.startswith("gemini"):
        if not GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY não configurada, retornando texto original")
            return text
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            model = genai.GenerativeModel(AI_MODEL)
            response = model.generate_content(f"{AI_PROMPT}\n\n{text}")
            return response.text.strip()
        except Exception as e:
            print(f"ERROR: Erro no Gemini: {e}")
            return text
    else:
        print("WARNING: Modelo desconhecido, retornando texto original")
        return text


def send_to_notion(title, text):
    """Envia texto ao Notion como página"""
    blocks = [{"object": "block", "type": "paragraph", "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": chunk}}]
    }} for chunk in split_paragraphs(text)]

    payload = {
        "parent": {"database_id": NOTION_PARENT_ID},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": blocks
    }

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    resp = requests.post("https://api.notion.com/v1/pages",
                         headers=headers, json=payload, timeout=60)

    if resp.status_code == 200:
        print(f"INFO: Página '{title}' criada no Notion ({len(blocks)} blocos)")
    else:
        print(f"ERROR: Erro ao criar página no Notion: {resp.text}")


# ==============================
# Execução principal
# ==============================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python script.py <url1> [url2 ...]")
        sys.exit(1)

    urls = sys.argv[1:]

    for url in urls:
        # Se for playlist, expande para vídeos
        if "list=" in url:
            print(f"INFO: Obtendo vídeos da playlist {url}")
            try:
                videos = get_playlist_videos(url)
                urls.extend(videos)
            except Exception as e:
                print(f"ERROR: Falha ao obter playlist: {e}")
            continue

        # Caso seja um vídeo
        print(f"INFO: Processando vídeo {url}...")
        try:
            title, transcript = get_video_transcript(url)
            print(f"INFO: Transcrição obtida ({len(transcript)} caracteres)")
            processed = process_with_ai(transcript)
            print(f"INFO: Texto processado ({len(processed)} caracteres)")
            send_to_notion(title, processed)
        except Exception as e:
            print(f"ERROR: Falha ao processar vídeo {url}: {e}")
