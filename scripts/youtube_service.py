import os
import requests
import yt_dlp

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def get_transcript(video_url: str, lang: str = "pt") -> str:
    """Obtém a transcrição via Supadata API"""
    endpoint = "https://api.supadata.ai/youtube/transcript"
    headers = {"Authorization": f"Bearer {SUPADATA_API_KEY}"}
    params = {"url": video_url, "lang": lang}

    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("transcript", "")

def get_metadata(video_url: str) -> dict:
    """Obtém título e canal sem custo usando yt-dlp"""
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            "title": info.get("title"),
            "channel": info.get("uploader")
        }

def get_video_data(video_url: str, lang: str = "pt") -> dict:
    """Combina metadados + transcrição"""
    transcript = get_transcript(video_url, lang)
    metadata = get_metadata(video_url)
    return {
        "title": metadata["title"],
        "channel": metadata["channel"],
        "transcript": transcript
    }
