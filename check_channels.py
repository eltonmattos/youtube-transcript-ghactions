import os
import json
import requests
from datetime import datetime, timedelta

# Caminhos dos arquivos
CHANNELS_FILE = "channels.json"  # Lista de canais/playlist a monitorar
PLAYLIST_FILE = "playlist.json"  # Playlist local com vídeos encontrados

# Carrega API Key do YouTube (opcional)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return {"playlistId": None, "channels": []}
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_playlist():
    if not os.path.exists(PLAYLIST_FILE):
        return []
    with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_playlist(playlist):
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(playlist, f, indent=2, ensure_ascii=False)


def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)


def fetch_channel_videos(channel_id, published_after=None):
    if not YOUTUBE_API_KEY:
        print("[Aviso] Nenhuma API key definida. Modo offline: não será possível consultar novos vídeos.")
        return []

    params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": 10,
        "order": "date",
        "type": "video",
        "key": YOUTUBE_API_KEY
    }

    if published_after:
        params["publishedAfter"] = published_after.isoformat("T") + "Z"

    r = requests.get(f"{YOUTUBE_API_URL}/search", params=params)
    if r.status_code != 200:
        print(f"Erro ao buscar vídeos do canal {channel_id}: {r.text}")
        return []

    data = r.json()
    videos = []
    for item in data.get("items", []):
        videos.append({
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "publishedAt": item["snippet"]["publishedAt"],
            "channelId": channel_id
        })
    return videos


def main():
    channels_data = load_channels()
    playlist = load_playlist()

    playlist_id = channels_data.get("playlistId")
    channels = channels_data.get("channels", [])

    # Indexar vídeos já existentes para evitar duplicatas
    existing_ids = {video["videoId"] for video in playlist}

    for ch in channels:
        channel_id = ch.get("id")
        last_checked = ch.get("lastChecked")

        published_after = None
        if last_checked:
            try:
                published_after = datetime.fromisoformat(last_checked.replace("Z", ""))
            except Exception:
                published_after = datetime.utcnow() - timedelta(days=7)
        else:
            published_after = datetime.utcnow() - timedelta(days=7)

        videos = fetch_channel_videos(channel_id, published_after)
        new_videos = [v for v in videos if v["videoId"] not in existing_ids]
        if new_videos:
            print(f"Canal {ch.get('name')}: encontrados {len(new_videos)} vídeos novos")
            playlist.extend(new_videos)
            existing_ids.update(v["videoId"] for v in new_videos)

        # Atualizar data da última verificação
        ch["lastChecked"] = datetime.utcnow().isoformat() + "Z"

    save_playlist(playlist)
    save_channels(channels_data)
    print("Playlist atualizada com sucesso.")


if __name__ == "__main__":
    main()
