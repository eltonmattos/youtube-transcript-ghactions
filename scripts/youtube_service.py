import os
import requests
import yt_dlp

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def get_transcript(video_url: str, lang: str = "pt") -> str:
    headers = {
        "x-api-key": SUPADATA_API_KEY
    }

    params = {
        "url": video_url,
        "lang": lang,
        "text": True,
        "mode": "auto"
    }

    response = requests.get("https://api.supadata.ai/v1/transcript", headers=headers, params=params)

    if response.status_code == 200:
        return response.json().get("content", "")
    elif response.status_code == 202:
        job_id = response.json().get("jobId")
        return poll_for_transcript(job_id)
    else:
        response.raise_for_status()

def poll_for_transcript(job_id: str) -> str:
    headers = {
        "x-api-key": SUPADATA_API_KEY
    }

    while True:
        response = requests.get(f"https://api.supadata.ai/v1/transcript/{job_id}", headers=headers)
        if response.status_code == 200:
            return response.json().get("content", "")
        elif response.status_code == 202:
            continue
        else:
            response.raise_for_status()

def get_metadata(video_url: str) -> dict:
    """Obtém título e canal usando yt-dlp, com user-agent para evitar bloqueio"""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "forcejson": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "geo_bypass": True,
        "ignoreerrors": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            "title": info.get("title"),
            "channel": info.get("uploader")
        }

def get_video_data(video_url: str, lang: str = "pt") -> dict:
    """Combina metadados + transcricao"""
    transcript = get_transcript(video_url, lang)
    metadata = get_metadata(video_url)
    return {
        "title": metadata["title"],
        "channel": metadata["channel"],
        "transcript": transcript
    }
