"""prox routine — manage scheduled agent execution."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, gateway_post, gateway_delete, APIError

app = typer.Typer(help="Manage routines (scheduled agent execution).")
console = Console()


@app.command("list")
def list_routines():
    """List routines."""
    try:
        data = gateway_get("/build/routines")
        routines = data.get("routines", [])
        if not routines:
            console.print("[dim]No routines.[/dim]")
            return
        table = Table(title="Routines")
        table.add_column("ID", style="bold")
        table.add_column("Agent")
        table.add_column("Trigger")
        table.add_column("Status")
        for r in routines:
            trigger = r.get("trigger", {})
            ttype = trigger.get("type", "manual") if isinstance(trigger, dict) else str(trigger)
            st = r.get("status", "draft")
            st_style = "green" if st == "active" else "dim"
            table.add_row(r.get("id"), r.get("agent_id", ""), ttype, f"[{st_style}]{st}[/{st_style}]")
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("create")
def create_routine(
    id: str = typer.Option(..., "--id"),
    agent: str = typer.Option(..., "--agent", help="Agent ID"),
    prompt: str = typer.Option(..., "--prompt", help="Prompt to send"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron schedule (e.g. '0 6 * * *')"),
):
    """Create a routine."""
    payload = {"id": id, "agent_id": agent, "prompt": prompt, "status": "active"}
    if cron:
        payload["trigger"] = {"type": "cron", "schedule": cron}
    else:
        payload["trigger"] = {"type": "manual"}
    try:
        gateway_post("/build/routines", payload)
        console.print(f"[green]✓[/green] Routine created: {id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("trigger")
def trigger_routine(routine_id: str = typer.Argument(help="Routine ID")):
    """Manually trigger a routine."""
    try:
        data = gateway_post(f"/build/routines/{routine_id}/trigger")
        console.print(f"[green]✓[/green] Triggered: {routine_id}")
        if data.get("run_id"):
            console.print(f"  Run ID: {data['run_id']}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("delete")
def delete_routine(routine_id: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a routine."""
    if not confirm:
        typer.confirm(f"Delete routine '{routine_id}'?", abort=True)
    try:
        gateway_delete(f"/build/routines/{routine_id}")
        console.print(f"[green]✓[/green] Deleted: {routine_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
