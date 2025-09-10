#!/usr/bin/env python3
"""
music_cli.py — Cliente CLI para Music Daemon
Dependências: typer, rich, requests
"""

import subprocess
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
        subprocess.Popen(
            ["python3", "-m", "musicd"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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
            resp = requests.post(url, json=json or {}, timeout=15)
            return resp.json()
        except Exception as e:
            console.print(f"[red]Erro de conexão com daemon: {e}[/red]")
            raise

    def get(self, path: str, params: dict = None):  # type: ignore
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, params=params or {}, timeout=15)
            return resp.json()
        except Exception as e:
            console.print(f"[red]Erro de conexão com daemon: {e}[/red]")
            raise


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
    api = MusicAPI(**ctx.obj)
    resp = api.post("/queue", {"query": query})
    if resp.get("ok"):
        console.print("[green]✅ Música adicionada à fila[/green]")
        pretty_track(resp.get("item"))


@app.command()
def search(ctx: typer.Context, query: str = typer.Argument(..., help="Pesquisa no YouTube Music")):
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
        choice = Prompt.ask("Selecione um número para tocar/adicionar à fila", choices=[str(i) for i in range(1, len(results) + 1)])
        selected_track = results[int(choice) - 1]
        
        # Usa o endpoint `/play` para tocar imediatamente
        resp = api.post("/play", {"query": selected_track["webpage_url"]})
        if resp.get("ok"):
            console.print("[green]▶ Tocando agora[/green]")
            pretty_track(resp.get("track"))
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
                    output += f"🎵 [cyan]{now.get('title')}[/cyan] — [magenta]{now.get('artist')}[/magenta]\n"
                else:
                    output += "[dim]Nada tocando[/dim]\n"
                
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
                time.sleep(2) # Atualiza a cada 2 segundos
        except KeyboardInterrupt:
            console.print("\n[yellow]Saindo do monitor.[/yellow]")


@app.command("queue-list")
def queue_list(ctx: typer.Context):
    """Lista a fila de reprodução"""
    api = MusicAPI(**ctx.obj)
    resp = api.get("/queue")
    items: List[Dict] = resp.get("queue", [])
    # Adiciona a faixa atual ao início da fila para exibição
    status_resp = api.get("/status")
    if status_resp.get("now"):
        items.insert(0, status_resp["now"])
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


if __name__ == "__main__":
    app()
