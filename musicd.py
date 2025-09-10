#!/usr/bin/env python3
"""
musicd.py — Music Daemon com autoplay
Dependências: fastapi, uvicorn, python-mpv, yt-dlp, httpx
"""

import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from rich.console import Console
import yt_dlp
import mpv  # type: ignore
import uvicorn

# Adicione esta linha para garantir que o mpv.dll seja encontrado.
# O caminho para a pasta do MPV é adicionado ao PATH do ambiente.
os.environ["PATH"] = "C:\\mpv" + os.pathsep + os.environ["PATH"]

app = FastAPI(title="Music Daemon (YouTube Music)")

console = Console()

# Estado
queue: List[dict] = []
history: List[dict] = []
current_track: Optional[dict] = None
player_lock = asyncio.Lock()

# Player MPV configurado sem vídeo
player = mpv.MPV(
    # input_default_bindings=True, # Desabilitar para evitar inputs do terminal
    # input_vo_keyboard=True,
    osc=False,
    vo="null",  # sem janela de vídeo
    audio_display=False,
    ytdl=True,  # deixa o mpv lidar com urls do yt
    # quiet=True, # Desabilitar para ver logs do mpv/yt-dlp em caso de erro
)


# Modelo para requests
class PlayRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    query: str


# Função para buscar no YouTube
def search_list(query: str, max_results: int = 10) -> list:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        if not info or "entries" not in info or not info["entries"]:
            return []

        return [
            {
                "title": entry.get("title"),
                "webpage_url": entry.get("webpage_url"),
                "duration": entry.get("duration"),
                "duration_str": entry.get("duration_string"),
                "artist": entry.get("uploader"),
                "channel": entry.get("channel"),
                "thumbnail": entry.get("thumbnail"),
            }
            for entry in info["entries"]
        ]


@app.post("/search")
async def search(req: SearchRequest):
    results = search_list(req.query)
    return {"ok": True, "results": results}


# Função para buscar no YouTube
def search_youtube(query: str) -> Optional[dict]:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch1",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        try:
            info = ydl.extract_info(query, download=False)
            # Pega o primeiro resultado da busca ou do playlist
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            # Se ainda não for um vídeo válido, retorna None
            if not info or "webpage_url" not in info:
                return None

            return {
                "title": info.get("title"),
                "webpage_url": info.get("webpage_url"),
                "duration": info.get("duration"),
                "duration_str": info.get("duration_string"),
                "artist": info.get("uploader"),
                "channel": info.get("channel"),
                "thumbnail": info.get("thumbnail"),
            }
        except yt_dlp.utils.DownloadError:
            return None


# Função que roda o player em thread separada
def play_track(url: str):
    """Função de bloqueio que toca a música e espera ela terminar."""
    player.play(url)
    player.wait_for_playback()  # Espera a música terminar


# Tocar próxima da fila
async def play_next():
    """Pega a próxima música da fila e a toca."""
    global current_track
    async with player_lock:
        if not queue:
            current_track = None
            return

        current_track = queue.pop(0)
        history.append(current_track)

        console.log(f"Autoplay: Tocando '{current_track['title']}'")
        # Executa a função de bloqueio em uma thread separada gerenciada pelo asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, play_track, current_track["webpage_url"])

        # Após a música terminar, o loop principal vai chamar play_next() novamente
        current_track = None
        console.log("Autoplay: Faixa terminada. Procurando a próxima.")


async def player_loop():
    """Loop principal que gerencia o autoplay."""
    while True:
        # Se o player não estiver tocando nada e houver músicas na fila,
        # e não houver um bloqueio ativo, inicia a próxima música.
        if not player.playback_time and queue and not player_lock.locked():
            asyncio.create_task(play_next())
        await asyncio.sleep(0.5)


@app.on_event("startup")
async def startup_event():
    """Inicia o loop de autoplay em segundo plano."""
    asyncio.create_task(player_loop())


# Endpoints
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
    global queue, current_track
    queue.clear()  # Limpa a fila
    player.stop()  # Para a música atual
    current_track = None
    return {"ok": True}


@app.post("/next")
async def next_track():
    """Força a passagem para a próxima música."""
    if not queue:
        player.stop()
        return {"ok": True, "message": "Fila vazia."}
    player.stop()  # Para a música atual, o player_loop cuidará da próxima
    await asyncio.sleep(0.5)  # Dá tempo para o loop iniciar a próxima
    return {"ok": True, "track": current_track}


@app.post("/play")
async def play(req: PlayRequest):
    track = search_youtube(req.query)
    if not track:
        return {"ok": False, "error": "Música não encontrada"}

    queue.insert(0, track)
    player.stop()  # Interrompe a atual para que o player_loop pegue a nova imediatamente

    # O player_loop vai pegar a nova música
    await asyncio.sleep(1)  # Dá um tempo para o loop reagir
    return {"ok": True, "track": track}


@app.post("/queue")
async def add_queue(req: PlayRequest):
    track = search_youtube(req.query)
    if not track:
        return {"ok": False, "error": "Música não encontrada"}
    queue.append(track)
    return {"ok": True, "item": track}


@app.get("/status")
async def status():
    return {"ok": True, "now": current_track, "queue": queue, "history": history}


def main():
    uvicorn.run("musicd:app", host="127.0.0.1", port=5000, reload=False)


if __name__ == "__main__":
    main()
