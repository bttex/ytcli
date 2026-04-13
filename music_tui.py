#!/usr/bin/env python3
"""
music_tui.py - Interface TUI para controlar o Music Daemon.
Dependencias: textual, requests
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static

DEFAULT_HOST = os.getenv("MUSICD_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("MUSICD_PORT", "5000"))


class APIError(RuntimeError):
    """Erro de comunicacao com o daemon."""


@dataclass
class MusicAPI:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}{path}", params=params or {}, timeout=20
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise APIError(str(exc)) from exc

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}", json=payload or {}, timeout=20
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise APIError(str(exc)) from exc

    def search(self, query: str) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/search", json={"query": query}, timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise APIError(str(exc)) from exc


def ensure_daemon(host: str, port: int) -> None:
    api = MusicAPI(host=host, port=port)
    try:
        api.get("/status")
        return
    except APIError:
        pass

    env = os.environ.copy()
    env["MUSICD_HOST"] = host
    env["MUSICD_PORT"] = str(port)

    commands = [["musicd"], [sys.executable, "-m", "musicd"]]
    started = False
    for command in commands:
        try:
            subprocess.Popen(
                command,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            started = True
            break
        except FileNotFoundError:
            continue

    if not started:
        raise APIError("Nao foi possivel iniciar o daemon automaticamente.")

    for _ in range(12):
        try:
            api.get("/status")
            return
        except APIError:
            time.sleep(0.5)

    raise APIError("Daemon nao respondeu apos tentativa de inicializacao.")


class MusicTUI(App[None]):
    TITLE = "YTCLI Music TUI"
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
        color: $text;
    }

    #title_bar {
        height: auto;
        margin: 0;
        padding: 0 1;
        background: $boost;
        color: $text;
    }

    #top_bar {
        height: auto;
        margin: 0;
        padding: 1 1;
        border: solid white;
    }

    #query_input {
        width: 1fr;
        min-width: 24;
    }

    #controls {
        height: auto;
        margin: 0;
        padding: 1;
        border: solid white;
    }

    Button {
        margin: 0 1;
    }

    #now_playing {
        margin: 0;
        padding: 1;
        border: solid white;
        min-height: 4;
    }

    .section_title {
        margin: 0;
        padding: 0 1;
        background: $boost;
        color: $text;
    }

    #tables {
        height: 1fr;
        margin: 0;
    }

    #results_section, #queue_section {
        height: 1fr;
        border: solid white;
        margin: 0;
    }

    #results_table, #queue_table {
        width: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Sair"),
        ("r", "refresh", "Atualizar"),
        ("p", "toggle_pause", "Pausar/Retomar"),
    ]

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        super().__init__()
        self.api = MusicAPI(host=host, port=port)
        self.results: list[dict[str, Any]] = []
        self.search_in_progress = False
        self.status_refresh_in_progress = False
        self.status_refresh_pending = False

    def compose(self) -> ComposeResult:
        yield Static("┌─ YTCLI MUSIC PLAYER ─┐", id="title_bar")
        with Horizontal(id="top_bar"):
            yield Input(placeholder="Buscar musica ou URL", id="query_input")
            yield Button("Buscar", id="search")
        with Horizontal(id="controls"):
            yield Button("Play", id="play")
            yield Button("Queue", id="queue")
            yield Button("Pause", id="pause")
            yield Button("Resume", id="resume")
            yield Button("Next", id="next")
            yield Button("Stop", id="stop")
            yield Button("Refresh", id="refresh")
        yield Static("[ Agora Tocando ]", id="now_playing")
        with Horizontal(id="tables"):
            with Vertical(id="results_section"):
                yield Static("[ Resultados ]", classes="section_title")
                yield DataTable(id="results_table")
            with Vertical(id="queue_section"):
                yield Static("[ Fila ]", classes="section_title")
                yield DataTable(id="queue_table")

    def on_mount(self) -> None:
        self.query_one("#results_table", DataTable).add_columns(
            "#", "Titulo", "Artista", "Duracao"
        )
        self.query_one("#queue_table", DataTable).add_columns(
            "#", "Titulo", "Artista", "Duracao"
        )
        self.set_interval(2.0, self.refresh_status)
        self.refresh_status()

    def action_refresh(self) -> None:
        self.refresh_status(force=True)

    def action_toggle_pause(self) -> None:
        try:
            status = self.api.get("/status")
            if status.get("now"):
                self.api.post("/pause")
            else:
                self.api.post("/resume")
        except APIError as exc:
            self.notify(f"Erro: {exc}", severity="error")
        finally:
            self.refresh_status(force=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id is None:
            return

        if button_id == "search":
            self.run_search()
            return

        if button_id == "play":
            self.play_query()
            return

        if button_id == "queue":
            self.queue_query()
            return

        if button_id == "refresh":
            self.refresh_status(force=True)
            return

        endpoint_map = {
            "pause": "/pause",
            "resume": "/resume",
            "next": "/next",
            "stop": "/stop",
        }
        endpoint = endpoint_map.get(button_id)
        if not endpoint:
            return

        try:
            self.api.post(endpoint)
        except APIError as exc:
            self.notify(f"Erro: {exc}", severity="error")
        finally:
            self.refresh_status(force=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "query_input":
            self.run_search()

    def _set_search_loading(self, is_loading: bool) -> None:
        self.search_in_progress = is_loading
        search_button = self.query_one("#search", Button)
        search_button.disabled = is_loading
        search_button.label = "Buscando..." if is_loading else "Buscar"

    def run_search(self) -> None:
        if self.search_in_progress:
            self.notify("Busca em andamento...", severity="warning")
            return

        query_input = self.query_one("#query_input", Input)
        query = query_input.value.strip()
        if not query:
            self.notify("Digite um termo para buscar.", severity="warning")
            return

        self._set_search_loading(True)
        worker = threading.Thread(
            target=self._run_search_request,
            args=(query,),
            daemon=True,
        )
        worker.start()

    def _run_search_request(self, query: str) -> None:
        try:
            response = self.api.search(query)
            self.call_from_thread(self._finish_search, response, None)
        except APIError as exc:
            self.call_from_thread(self._finish_search, None, str(exc))

    def _finish_search(
        self, response: dict[str, Any] | None, error_message: str | None
    ) -> None:
        self._set_search_loading(False)

        if error_message:
            self.notify(f"Erro na busca: {error_message}", severity="error")
            return

        if response is None:
            self.notify("Erro inesperado na busca.", severity="error")
            return

        self.results = response.get("results", [])
        self._render_results_table()

        if not self.results:
            self.notify("Nenhum resultado encontrado.", severity="warning")

    def _render_results_table(self) -> None:
        results_table = self.query_one("#results_table", DataTable)
        results_table.clear(columns=False)
        for idx, track in enumerate(self.results, start=1):
            results_table.add_row(
                str(idx),
                str(track.get("title") or "-"),
                str(track.get("artist") or track.get("uploader") or "-"),
                str(track.get("duration_str") or track.get("duration") or "-"),
            )

        if self.results:
            try:
                results_table.move_cursor(row=0, column=0)
            except Exception:
                pass

    def play_query(self) -> None:
        selected_track = self._get_selected_result_track()
        if not selected_track:
            self.notify(
                "Selecione uma musica na tabela de resultados.", severity="warning"
            )
            return

        query = str(selected_track.get("webpage_url") or "").strip()
        if not query:
            self.notify("Resultado selecionado sem URL valida.", severity="error")
            return

        try:
            response = self.api.post("/play", {"query": query})
            if not response.get("ok"):
                self.notify(response.get("error", "Falha ao tocar."), severity="error")
            else:
                self.notify("Resultado selecionado tocando agora.")
        except APIError as exc:
            self.notify(f"Erro: {exc}", severity="error")
        finally:
            self.refresh_status(force=True)

    def queue_query(self) -> None:
        selected_track = self._get_selected_result_track()
        if not selected_track:
            self.notify(
                "Selecione uma musica na tabela de resultados.", severity="warning"
            )
            return

        query = str(selected_track.get("webpage_url") or "").strip()
        if not query:
            self.notify("Resultado selecionado sem URL valida.", severity="error")
            return

        try:
            response = self.api.post("/queue", {"query": query})
            if response.get("ok"):
                self.notify("Resultado selecionado adicionado a fila.")
            else:
                self.notify(
                    response.get("error", "Falha ao adicionar."), severity="error"
                )
        except APIError as exc:
            self.notify(f"Erro: {exc}", severity="error")
        finally:
            self.refresh_status()

    def _get_selected_result_track(self) -> dict[str, Any] | None:
        table = self.query_one("#results_table", DataTable)
        if not self.results or table.row_count == 0:
            return None

        cursor_row = table.cursor_row
        if cursor_row is None:
            return None
        if cursor_row < 0 or cursor_row >= table.row_count:
            return None

        try:
            row = table.get_row_at(cursor_row)
            idx = int(str(row[0])) - 1
        except Exception:
            return None

        if idx < 0 or idx >= len(self.results):
            return None
        return self.results[idx]

    def refresh_status(self, force: bool = False) -> None:
        if self.status_refresh_in_progress:
            if force:
                self.status_refresh_pending = True
            return

        self.status_refresh_in_progress = True
        worker = threading.Thread(target=self._run_status_request, daemon=True)
        worker.start()

    def _run_status_request(self) -> None:
        try:
            response = self.api.get("/status")
            self.call_from_thread(self._finish_refresh_status, response, None)
        except APIError as exc:
            self.call_from_thread(self._finish_refresh_status, None, str(exc))

    def _finish_refresh_status(
        self, response: dict[str, Any] | None, error_message: str | None
    ) -> None:
        self.status_refresh_in_progress = False

        now_playing = self.query_one("#now_playing", Static)
        queue_table = self.query_one("#queue_table", DataTable)

        if error_message:
            now_playing.update(f"Daemon indisponivel: {error_message}")
            return

        if response is None:
            now_playing.update("Daemon indisponivel: resposta vazia")
            return

        now = response.get("now")
        queue = response.get("queue") or []

        if now:
            now_playing.update(
                "┌─ TOCANDO AGORA ─┐\n"
                f"│ Título: {now.get('title', '-')}\n"
                f"│ Artista: {now.get('artist', now.get('uploader', '-'))}\n"
                f"│ Duração: {now.get('duration_str', now.get('duration', '-'))}"
            )
        else:
            now_playing.update("┌─ TOCANDO AGORA ─┐\n│ [Nada tocando]")

        queue_table.clear(columns=False)
        for idx, track in enumerate(queue, start=1):
            queue_table.add_row(
                str(idx),
                str(track.get("title") or "-"),
                str(track.get("artist") or track.get("uploader") or "-"),
                str(track.get("duration_str") or track.get("duration") or "-"),
            )

        if self.status_refresh_pending:
            self.status_refresh_pending = False
            self.refresh_status()


def main() -> None:
    host = os.getenv("MUSICD_HOST", DEFAULT_HOST)
    port = int(os.getenv("MUSICD_PORT", str(DEFAULT_PORT)))

    try:
        ensure_daemon(host=host, port=port)
    except APIError as exc:
        print(f"Erro ao iniciar daemon: {exc}")
        raise SystemExit(1)

    app = MusicTUI(host=host, port=port)
    app.run()


if __name__ == "__main__":
    main()
