#!/usr/bin/env python3
"""
music_tui.py — TUI para Music Daemon
Dependências: textual, requests, asyncio, subprocess, time
"""

import asyncio
import requests
import subprocess
import time
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Header, Footer, Input, DataTable
from textual.containers import Horizontal, Vertical

DAEMON_URL = "http://127.0.0.1:5000"


class MusicTUI(App):
    CSS_PATH = "music_tui.css"
    TITLE = "MusicTUI"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Horizontal(
                Input(placeholder="Pesquisar música...", id="search_input"),
                Button("Play", id="btn_play"),
                Button("Pause", id="btn_pause"),
                Button("Resume", id="btn_resume"),
                Button("Next", id="btn_next"),
                id="controls",
            ),
            Static("🎵 Agora tocando: —", id="now_playing"),
            Static("Fila de reprodução:", id="queue_label"),
            DataTable(id="queue_table"),
            id="main",
        )
        yield Footer()

    async def on_mount(self):
        # Referências
        self.queue_table = self.query_one("#queue_table", DataTable)
        self.now_playing = self.query_one("#now_playing", Static)
        self.queue_table.add_columns("Título", "Artista", "Duração")

        # Garante que o daemon esteja rodando
        await self.ensure_daemon()

        # Loop de atualização automática
        self.set_interval(1, self.update_status)

    # ---------------------------
    # Garantir daemon rodando
    # ---------------------------
    async def ensure_daemon(self):
        try:
            requests.get(f"{DAEMON_URL}/status", timeout=2)
        except Exception:
            self.now_playing.update("🔄 Iniciando daemon...")
            subprocess.Popen(
                ["python3", "-m", "musicd"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # espera subir
            for _ in range(10):
                try:
                    requests.get(f"{DAEMON_URL}/status", timeout=2)
                    self.now_playing.update("✅ Daemon pronto")
                    return
                except Exception:
                    await asyncio.sleep(1)
            self.now_playing.update("❌ Falha ao iniciar daemon")

    # ---------------------------
    # Helpers assíncronos para API
    # ---------------------------
    async def api_post(self, path, json=None):
        return await asyncio.to_thread(
            lambda: requests.post(f"{DAEMON_URL}{path}", json=json or {}, timeout=10)
        )

    async def api_get(self, path):
        return await asyncio.to_thread(
            lambda: requests.get(f"{DAEMON_URL}{path}", timeout=5).json()
        )

    # ---------------------------
    # Atualização do TUI
    # ---------------------------
    async def update_status(self):
        try:
            resp = await self.api_get("/status")
            now = resp.get("now")
            queue = resp.get("queue", [])

            # Atualiza música atual
            if now:
                self.now_playing.update(
                    f"🎵 {now.get('title', '—')} — {now.get('artist', '—')}"
                )
            else:
                self.now_playing.update("Nada tocando")

            # Atualiza fila
            self.queue_table.clear()
            for t in queue:
                self.queue_table.add_row(
                    t.get("title", "—"),
                    t.get("artist", t.get("uploader", "—")),
                    str(t.get("duration_str", t.get("duration", "—"))),
                )
        except Exception:
            pass

    # ---------------------------
    # Eventos de botões
    # ---------------------------
    async def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        input_box = self.query_one("#search_input", Input)
        query = input_box.value.strip()

        try:
            if btn_id == "btn_play" and query:
                await self.api_post("/play", json={"query": query})
            elif btn_id == "btn_pause":
                await self.api_post("/pause")
            elif btn_id == "btn_resume":
                await self.api_post("/resume")
            elif btn_id == "btn_next":
                await self.api_post("/next")
        except Exception as e:
            self.now_playing.update(f"Erro de conexão: {e}")

        # Atualiza fila após ação
        await self.update_status()


if __name__ == "__main__":
    MusicTUI().run()
