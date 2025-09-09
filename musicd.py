#!/usr/bin/env python3
"""
musicd.py — Music Daemon com autoplay
Dependências: fastapi, uvicorn, python-mpv, yt-dlp
"""

import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import yt_dlp
import mpv
import threading

app = FastAPI(title="Music Daemon (YouTube Music)")

# Estado
queue: List[dict] = []
history: List[dict] = []
current_track: Optional[dict] = None

# Player MPV configurado sem vídeo
player = mpv.MPV(
    input_default_bindings=True,
    input_vo_keyboard=True,
    osc=False,
    vo="null",  # sem janela de vídeo
    audio_display=False,
    ytdl=True,  # deixa o mpv lidar com urls do yt
    quiet=True,
)


# Modelo para requests
class PlayRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    query: str

# Função para buscar no YouTube
def search_list(query: str, max_results: int = 5) -> list:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        tracks = []
        if "entries" in info:
            for entry in info["entries"]:
                tracks.append({
                    "title": entry.get("title"),
                    "webpage_url": entry.get("webpage_url"),
                    "duration": entry.get("duration"),
                    "artist": entry.get("uploader"),
                })
        return tracks

@app.post("/search")
async def search(req: SearchRequest):
    results = search_list(req.query)
    return {"ok": True, "results": results}

# Função para buscar no YouTube
def search_youtube(query: str) -> dict:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch1",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title"),
            "url": info.get("url"),
            "webpage_url": info.get("webpage_url"),
            "duration": info.get("duration"),
            "artist": info.get("uploader"),
        }


# Função que roda o player em thread separada
def play_track(url: str):
    player.play(url)


# Tocar próxima da fila
async def play_next():
    global current_track
    if not queue:
        current_track = None
        return
    current_track = queue.pop(0)
    history.append(current_track)
    threading.Thread(
        target=play_track, args=(current_track["webpage_url"],), daemon=True
    ).start()


# Callback do mpv: quando terminar, toca próxima
async def player_loop():
    global current_track
    while True:
        if current_track and player.playback_status == "stopped":
            await play_next()
        await asyncio.sleep(0.5)


# Endpoints
@app.post("/play")
async def play(req: PlayRequest):
    global current_track
    track = search_youtube(req.query)
    queue.insert(0, track)
    await play_next()
    return {"ok": True, "track": current_track}


@app.post("/queue")
async def add_queue(req: PlayRequest):
    track = search_youtube(req.query)
    queue.append(track)
    return {"ok": True, "item": track}


@app.get("/queue")
async def get_queue():
    return {"ok": True, "queue": queue}


@app.post("/pause")
async def pause():
    player.pause = True
    return {"ok": True}


@app.post("/resume")
async def resume():
    player.pause = False
    return {"ok": True}


@app.post("/stop")
async def stop():
    player.stop()
    return {"ok": True}


@app.post("/next")
async def next_track():
    await play_next()
    return {"ok": True, "track": current_track}


@app.get("/status")
async def status():
    return {"ok": True, "now": current_track, "queue": queue, "history": history}


if __name__ == "__main__":
    import uvicorn
    import asyncio

    loop = asyncio.get_event_loop()
    loop.create_task(player_loop())
    uvicorn.run("musicd:app", host="127.0.0.1", port=5000, reload=True)
