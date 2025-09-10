#!/usr/bin/env python3
"""
music_cli.py — Cliente CLI para Music Daemon
Dependências: typer, rich, requests
"""

import subprocess
import sys
import time
import os
from typing import Optional, List, Dict
import requests
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live

app = typer.Typer(help="Cliente CLI para Music Daemon (yt-dlp + mpv)")
console = Console()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def ensure_daemon():
    """Garante que o daemon esteja rodando"""
    url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/status"
    try:
        requests.get(url, timeout=2)
        return
    except Exception:
        console.print("[yellow]🔄 Iniciando daemon...[/yellow]")
        # Usa o entry point 'musicd' definido no pyproject.toml.
        # É mais robusto que chamar o módulo diretamente.
        subprocess.Popen(
            ["musicd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # esperar subir
        for _ in range(10):
            try:
                requests.get(url, timeout=2)
                console.print("[green]✅ Daemon pronto[/green]")
                return
            except Exception:
                time.sleep(1)
        console.print("[red]❌ Falha ao iniciar daemon[/red]")
        raise typer.Exit(1)


# -------------------------------
# Helper: API Client
# -------------------------------
class MusicAPI:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.getenv("MUSICD_HOST") or DEFAULT_HOST
        self.port = port or int(os.getenv("MUSICD_PORT") or DEFAULT_PORT)
        self.base_url = f"http://{self.host}:{self.port}"

    def post(self, path: str, json: dict = None):  # type: ignore
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(url, json=json or {}, timeout=20)
            resp.raise_for_status()  # Lança erro para status 4xx/5xx
            return resp.json()
        except requests.exceptions.ConnectionError:
            console.print(
                f"[red]❌ Erro: Não foi possível conectar ao daemon em {self.base_url}. Ele está rodando?[/red]"
            )
            raise typer.Exit(1)
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Erro na comunicação com o daemon: {e}[/red]")
            raise typer.Exit(1)

    def get(self, path: str, params: dict = None):  # type: ignore
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, params=params or {}, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            console.print(
                f"[red]❌ Erro: Não foi possível conectar ao daemon em {self.base_url}. Ele está rodando?[/red]"
            )
            raise typer.Exit(1)
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Erro na comunicação com o daemon: {e}[/red]")
            raise typer.Exit(1)


# -------------------------------
# Helper: Pretty Print Track
# -------------------------------
def pretty_track(track: Dict):
    if not track:
        return
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=3)
    table.add_row("🎵 Título", track.get("title", "Desconhecido"))
    table.add_row(
        "👤 Artista", track.get("artist", track.get("uploader", "Desconhecido"))
    )
    table.add_row(
        "⏱ Duração", str(track.get("duration_str", track.get("duration", "—")))
    )
    table.add_row("🔗 URL", track.get("webpage_url", "—"))
    console.print(Panel(table, title="Faixa", expand=False))


# -------------------------------
# CLI Commands
# -------------------------------
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    host: Optional[str] = typer.Option(None, "--host", "-H", help="Host do daemon"),
    port: Optional[int] = typer.Option(None, "--port", "-P", help="Porta do daemon"),
):
    ctx.obj = {"host": host, "port": port}
    # 🔄 Garante que o daemon esteja rodando antes de qualquer comando
    ensure_daemon()


@app.command()
def play(
    ctx: typer.Context, query: str = typer.Argument(..., help="Nome ou URL da música")
):
    """Toca música imediatamente"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/play", {"query": query})
    if resp.get("ok"):
        console.print("[green]▶ Tocando agora[/green]")
        pretty_track(resp.get("track"))


@app.command()
def pause(ctx: typer.Context):
    """Pausa reprodução"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/pause")
    if resp.get("ok"):
        console.print("[yellow]⏸ Pausado[/yellow]")


@app.command()
def resume(ctx: typer.Context):
    """Retoma reprodução"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/resume")
    if resp.get("ok"):
        console.print("[green]▶ Resumido[/green]")


@app.command()
def stop(ctx: typer.Context):
    """Para a reprodução atual"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/stop")
    if resp.get("ok"):
        console.print("[red]⏹ Parado[/red]")


@app.command()
def next(ctx: typer.Context):
    """Próxima faixa"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/next")
    if resp.get("ok"):
        console.print("[green]⏭ Próxima faixa[/green]")
        pretty_track(resp.get("track"))


@app.command("queue-add")
def queue_add(
    ctx: typer.Context, query: str = typer.Argument(..., help="Adicionar música à fila")
):
    """Adiciona uma música ao final da fila."""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/queue", {"query": query})
    if resp.get("ok"):
        console.print("[green]✅ Música adicionada à fila[/green]")
        pretty_track(resp.get("item"))


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Pesquisa no YouTube Music"),
):
    """Busca por músicas e as adiciona à fila"""
    api = MusicAPI(**ctx.obj)
    resp = api.post("/search", {"query": query})
    if not resp.get("ok"):
        console.print("[red]❌ Erro na busca.[/red]")
        return
    results = resp.get("results", [])
    if not results:
        console.print("[dim]Nenhum resultado encontrado.[/dim]")
        return

    # Exibe os resultados em uma tabela Rich
    table = Table(title="Resultados da busca")
    table.add_column("#", style="dim", width=4)
    table.add_column("Título", style="cyan", no_wrap=True)
    table.add_column("Artista", style="magenta", no_wrap=True)
    table.add_column("Duração", style="dim", width=10)
    for i, t in enumerate(results, start=1):
        table.add_row(
            str(i),
            t.get("title", "—"),
            t.get("artist", t.get("uploader", "—")),
            str(t.get("duration", "—")),
        )
    console.print(table)

    # Pede ao usuário para escolher um item
    try:
        track_choice = Prompt.ask(
            "Selecione um número",
            choices=[str(i) for i in range(1, len(results) + 1)],
            prompt_suffix=" (ou pressione Ctrl+C para cancelar): ",
        ) # type: ignore
        selected_track = results[int(track_choice) - 1]

        action_choice = Prompt.ask(
            "O que você quer fazer?",
            choices=["play", "queue"],
            default="play",
        )
        endpoint = f"/{action_choice}"
        resp = api.post(endpoint, {"query": selected_track["webpage_url"]})

        if resp.get("ok"):
            message = (
                "▶ Tocando agora" if action_choice == "play" else "✅ Adicionado à fila"
            )
            console.print(f"[green]{message}[/green]")
            pretty_track(resp.get("track") or resp.get("item"))
    except KeyboardInterrupt:
        console.print("\n[yellow]Ação cancelada.[/yellow]")


@app.command()
def monitor(ctx: typer.Context):
    """Monitora o status do reprodutor em tempo real (Ctrl+C para sair)"""
    api = MusicAPI(**ctx.obj)
    with Live(auto_refresh=False) as live:
        try:
            while True:
                resp = api.get("/status")
                now = resp.get("now")
                queue = resp.get("queue", [])

                # Renderiza o status
                output = ""
                if now:
                    output += f"[bold green]▶ Agora tocando[/bold green]\n"
                    # Aqui você pode usar uma função para formatar a saída
                    output += f"🎵 [cyan]{now.get('title')}[/cyan]\n   └─ [magenta]{now.get('artist')}[/magenta]\n"
                else:
                    output += "[bold dim]⏹ Nada tocando[/bold dim]\n"

                # Se nada estiver tocando e a fila estiver vazia, pergunta por uma nova música
                if not now and not queue:
                    live.update(output)  # Mostra o status final
                    live.refresh()
                    try:
                        # Pausa o live para não interferir com o prompt
                        with live.console.capture():
                            query = Prompt.ask(
                                "\n[bold yellow]A fila acabou! Qual a próxima música?[/bold yellow] (ou pressione Ctrl+C para sair)"
                            )
                        if query:
                            console.print(f"Tocando '{query}'...")
                            api.post("/play", {"query": query})
                            # Continua o loop para atualizar o status
                            continue
                    except (KeyboardInterrupt, typer.Exit):
                        # Se o usuário cancelar, sai do monitor
                        break
                    except Exception:
                        break  # Sai em caso de outro erro
                output += f"\n[blue]Tamanho da fila:[/blue] {len(queue)}\n"

                # Formata a fila em uma tabela
                if queue:
                    table = Table(title="Fila de reprodução")
                    table.add_column("#", style="dim", width=4)
                    table.add_column("Título", style="cyan")
                    table.add_column("Artista", style="magenta")
                    for i, t in enumerate(queue, start=1):
                        table.add_row(
                            str(i),
                            t.get("title", "—"),
                            t.get("artist", t.get("uploader", "—")),
                        )
                    output += str(table)

                live.update(output)
                live.refresh()
                time.sleep(2)  # Atualiza a cada 2 segundos
        except KeyboardInterrupt:
            console.print("\n[yellow]Saindo do monitor.[/yellow]")
        except typer.Exit:
            # Impede que a mensagem de erro da API seja mostrada ao sair do monitor
            pass


@app.command("queue-list")
def queue_list(ctx: typer.Context):
    """Lista a fila de reprodução"""
    api = MusicAPI(**ctx.obj)
    resp = api.get("/queue")
    items: List[Dict] = resp.get("queue", [])
    if not items:
        console.print("[dim]Fila vazia[/dim]")
        return
    table = Table(title="Fila")
    table.add_column("#", width=4)
    table.add_column("Título")
    table.add_column("Artista")
    table.add_column("Duração", width=10)
    for i, t in enumerate(items, start=1):
        table.add_row(
            str(i),
            t.get("title", "—"),
            t.get("artist", t.get("uploader", "—")),
            str(t.get("duration_str", t.get("duration", "—"))),
        )
    console.print(table)


@app.command()
def status(ctx: typer.Context):
    """Mostra música atual e fila"""
    api = MusicAPI(**ctx.obj)
    resp = api.get("/status")
    now = resp.get("now")
    queue = resp.get("queue", [])
    if now:
        console.print("[bold green]▶ Agora tocando[/bold green]")
        pretty_track(now)
    else:
        console.print("[dim]Nada tocando[/dim]")
    console.print(f"[blue]Tamanho da fila:[/blue] {len(queue)}")


def main_cli():
    """Ponto de entrada para o console_script."""
    app()


if __name__ == "__main__":
    main_cli()
