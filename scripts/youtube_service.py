# -*- coding: utf-8 -*-
import os
import requests

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def get_transcript(video_url: str, lang: str = "pt") -> str:
    """
    Obtém a transcrição via Supadata API
    """
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
    """
    Aguarda a conclusão do job de transcrição na Supadata
    """
    headers = {"x-api-key": SUPADATA_API_KEY}

    while True:
        response = requests.get(f"https://api.supadata.ai/v1/transcript/{job_id}", headers=headers)
        if response.status_code == 200:
            return response.json().get("content", "")
        elif response.status_code == 202:
            continue
        else:
            response.raise_for_status()


def get_metadata(video_url: str) -> dict:
    """
    Obtém título e canal do vídeo usando oEmbed do YouTube (sem cookies)
    """
    endpoint = "https://www.youtube.com/oembed"
    params = {"url": video_url, "format": "json"}

    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    data = response.json()

    return {
        "title": data.get("title"),
        "channel": data.get("author_name")
    }


def get_video_data(video_url: str, lang: str = "pt") -> dict:
    """
    Combina metadados + transcrição
    """
    transcript = get_transcript(video_url, lang)
    metadata = get_metadata(video_url)

    return {
        "title": metadata["title"],
        "channel": metadata["channel"],
        "transcript": transcript
    }
