"""prox secret — manage platform secrets."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, gateway_post, gateway_delete, APIError

app = typer.Typer(help="Manage platform secrets.")
console = Console()


@app.command("list")
def list_secrets():
    """List secrets (names only, never values)."""
    try:
        data = gateway_get("/build/secrets")
        secrets = data.get("secrets", [])
        if not secrets:
            console.print("[dim]No secrets.[/dim]")
            return
        for s in secrets:
            console.print(f"  • {s.get('name', s) if isinstance(s, dict) else s}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("set")
def set_secret(
    name: str = typer.Argument(help="Secret name"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Secret value"),
    from_file: Optional[str] = typer.Option(None, "--from-file", help="Read value from file"),
):
    """Set a secret."""
    if from_file:
        from pathlib import Path
        value = Path(from_file).read_text().strip()
    if not value:
        value = typer.prompt("Secret value", hide_input=True)
    try:
        gateway_post("/build/secrets", {"name": name, "value": value})
        console.print(f"[green]✓[/green] Secret set: {name}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("delete")
def delete_secret(name: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a secret."""
    if not confirm:
        typer.confirm(f"Delete secret '{name}'?", abort=True)
    try:
        gateway_delete(f"/build/secrets/{name}")
        console.print(f"[green]✓[/green] Deleted: {name}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
