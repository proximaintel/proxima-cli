"""prox knowledge — manage knowledge sources and bases."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..api import gateway_get, gateway_post, gateway_delete, APIError

app = typer.Typer(help="Manage knowledge sources and bases.")
console = Console()

source_app = typer.Typer(help="Manage knowledge sources.")
app.add_typer(source_app, name="source")

base_app = typer.Typer(help="Manage knowledge bases.")
app.add_typer(base_app, name="base")


@source_app.command("list")
def list_sources():
    """List knowledge sources."""
    try:
        data = gateway_get("/build/knowledge/sources")
        sources = data.get("sources", [])
        if not sources:
            console.print("[dim]No sources.[/dim]")
            return
        table = Table(title="Knowledge Sources")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Provider")
        for s in sources:
            table.add_row(s.get("id"), s.get("name", ""), s.get("provider", ""))
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@source_app.command("create")
def create_source(
    id: str = typer.Option(..., "--id"),
    name: str = typer.Option(..., "--name"),
    provider: str = typer.Option(..., "--provider", help="azure_blob, s3, snowflake, etc."),
    secret: Optional[str] = typer.Option(None, "--secret", help="Secret name for credentials"),
    container: Optional[str] = typer.Option(None, "--container"),
    path: Optional[str] = typer.Option(None, "--path"),
):
    """Create a knowledge source."""
    payload = {"id": id, "name": name, "provider": provider}
    if secret:
        payload["credential_secret"] = secret
    if container:
        payload["container"] = container
    if path:
        payload["path"] = path
    try:
        gateway_post("/build/knowledge/sources", payload)
        console.print(f"[green]✓[/green] Source created: {id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@source_app.command("test")
def test_source(source_id: str = typer.Argument(help="Source ID to test")):
    """Test a source connection."""
    try:
        data = gateway_post(f"/build/knowledge/sources/{source_id}/test")
        if data.get("success"):
            console.print(f"[green]✓[/green] Connection successful ({data.get('rows', '?')} rows)")
        else:
            console.print(f"[red]✗[/red] {data.get('error', 'Connection failed')}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@source_app.command("delete")
def delete_source(source_id: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a knowledge source."""
    if not confirm:
        typer.confirm(f"Delete source '{source_id}'?", abort=True)
    try:
        gateway_delete(f"/build/knowledge/sources/{source_id}")
        console.print(f"[green]✓[/green] Deleted: {source_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@base_app.command("list")
def list_bases():
    """List knowledge bases."""
    try:
        data = gateway_get("/build/knowledge/bases")
        bases = data.get("bases", [])
        if not bases:
            console.print("[dim]No bases.[/dim]")
            return
        table = Table(title="Knowledge Bases")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Sources", justify="right")
        for b in bases:
            table.add_row(b.get("id"), b.get("name", ""), str(len(b.get("sources", []))))
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@base_app.command("create")
def create_base(
    id: str = typer.Option(..., "--id"),
    name: str = typer.Option(..., "--name"),
    sources: str = typer.Option(..., "--sources", help="Comma-separated source IDs"),
):
    """Create a knowledge base."""
    try:
        gateway_post("/build/knowledge/bases", {"id": id, "name": name, "sources": sources.split(",")})
        console.print(f"[green]✓[/green] Base created: {id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@base_app.command("delete")
def delete_base(base_id: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a knowledge base."""
    if not confirm:
        typer.confirm(f"Delete base '{base_id}'?", abort=True)
    try:
        gateway_delete(f"/build/knowledge/bases/{base_id}")
        console.print(f"[green]✓[/green] Deleted: {base_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
