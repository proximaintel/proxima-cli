"""prox toolbox — manage toolboxes (tool containers)."""

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..api import gateway_get, gateway_post, gateway_delete, APIError
from ..config import get_value

app = typer.Typer(help="Manage toolboxes.")
console = Console()


@app.command("list")
def list_toolboxes():
    """List registered toolboxes."""
    try:
        data = gateway_get("/build/toolboxes")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    toolboxes = data.get("toolboxes", [])
    if not toolboxes:
        console.print("[dim]No toolboxes registered.[/dim]")
        return

    table = Table(title=f"Toolboxes ({len(toolboxes)})")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Tools", justify="right")
    table.add_column("Endpoint", style="dim")

    for t in toolboxes:
        table.add_row(t.get("id"), t.get("name", ""), str(len(t.get("tools", []))), t.get("endpoint", ""))

    console.print(table)


@app.command("register")
def register_toolbox(
    id: str = typer.Option(..., "--id", help="Toolbox ID"),
    endpoint: str = typer.Option(..., "--endpoint", help="Toolbox HTTP endpoint"),
    name: Optional[str] = typer.Option(None, "--name", help="Display name"),
    discover: bool = typer.Option(False, "--discover", help="Auto-discover tools from OpenAPI"),
):
    """Register an existing toolbox endpoint."""
    try:
        gateway_post("/build/toolboxes", {
            "id": id,
            "name": name or id,
            "endpoint": endpoint,
            "type": "openapi",
        })
        if discover:
            gateway_post("/build/toolboxes/discover", {"toolbox_id": id})
            console.print(f"[green]✓[/green] Registered + discovered tools: {id}")
        else:
            console.print(f"[green]✓[/green] Registered: {id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("discover")
def discover_tools(
    endpoint: str = typer.Option(None, "--endpoint", help="Discover from URL"),
    toolbox_id: str = typer.Option(None, "--id", help="Re-discover existing toolbox"),
):
    """Discover tools from an OpenAPI endpoint."""
    try:
        payload = {}
        if toolbox_id:
            payload["toolbox_id"] = toolbox_id
        if endpoint:
            payload["endpoint"] = endpoint
        data = gateway_post("/build/toolboxes/discover", payload)
        tools = data.get("tools", [])
        console.print(f"[green]✓[/green] Discovered {len(tools)} tools")
        for t in tools:
            console.print(f"  • {t.get('name', t)}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("deploy")
def deploy_toolbox(
    from_path: Path = typer.Option(..., "--from", help="Path to toolbox directory"),
    name: str = typer.Option(..., "--name", help="Toolbox name/ID"),
):
    """Build, push, and register a toolbox from source."""
    registry = get_value("registry")
    if not registry:
        console.print("[red]Error:[/red] No registry configured. Run: prox config set registry <acr>")
        raise typer.Exit(1)

    if not (from_path / "Dockerfile").exists():
        console.print(f"[red]Error:[/red] No Dockerfile in {from_path}")
        raise typer.Exit(1)

    image = f"{registry}/{name}:latest"
    console.print(f"Building {image}...")

    r = subprocess.run(["docker", "build", "--platform", "linux/amd64", "-t", image, "."], cwd=from_path, capture_output=True, text=True)
    if r.returncode != 0:
        console.print(f"[red]Build failed:[/red]\n{r.stderr[:500]}")
        raise typer.Exit(1)

    console.print("Pushing...")
    r = subprocess.run(["docker", "push", image], capture_output=True, text=True)
    if r.returncode != 0:
        console.print(f"[red]Push failed:[/red]\n{r.stderr[:500]}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Deployed: {image}")


@app.command("delete")
def delete_toolbox(
    toolbox_id: str = typer.Argument(help="Toolbox ID"),
    confirm: bool = typer.Option(False, "--yes", "-y"),
):
    """Delete a toolbox."""
    if not confirm:
        typer.confirm(f"Delete toolbox '{toolbox_id}'?", abort=True)
    try:
        gateway_delete(f"/build/toolboxes/{toolbox_id}")
        console.print(f"[green]✓[/green] Deleted: {toolbox_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
