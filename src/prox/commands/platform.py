"""prox platform — health, status, service management."""

import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, APIError
from ..config import get_value

app = typer.Typer(help="Platform health and status.")
console = Console()


@app.command("health")
def health():
    """Check platform health."""
    gateway = get_value("gateway") or "not configured"
    console.print(f"\n  [bold]Platform Health[/bold]  ({gateway})\n")

    services = [
        ("Gateway", "/health"),
        ("Orchestrator", "/orchestrator/health"),
        ("Knowledge", "/knowledge/health"),
        ("Runtime", "/runtime/health"),
    ]

    for name, path in services:
        try:
            data = gateway_get(path)
            status = data.get("status", "ok")
            console.print(f"  [green]●[/green] {name:15} {status}")
        except APIError:
            console.print(f"  [red]●[/red] {name:15} unreachable")
        except Exception:
            console.print(f"  [red]●[/red] {name:15} error")

    console.print()


@app.command("status")
def status():
    """Show platform status summary."""
    try:
        data = gateway_get("/health")
        console.print(f"\n  Gateway:    [green]healthy[/green]")
        console.print(f"  Version:    {data.get('version', '—')}")
        console.print(f"  Agents:     {data.get('agents_registered', '—')}")
        console.print(f"  Uptime:     {data.get('uptime', '—')}")
    except APIError as e:
        console.print(f"  Gateway:    [red]error[/red] ({e.detail[:100]})")
    console.print()
