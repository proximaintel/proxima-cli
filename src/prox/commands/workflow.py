"""prox workflow — manage multi-agent workflows."""

from pathlib import Path
from typing import Optional
import typer
import yaml
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, gateway_post, gateway_put, gateway_delete, APIError

app = typer.Typer(help="Manage workflows.")
console = Console()


@app.command("list")
def list_workflows():
    """List workflows."""
    try:
        data = gateway_get("/build/workflows")
        workflows = data.get("workflows", [])
        if not workflows:
            console.print("[dim]No workflows.[/dim]")
            return
        table = Table(title="Workflows")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Nodes", justify="right")
        table.add_column("Status")
        table.add_column("Version", justify="right")
        for w in workflows:
            st = w.get("status", "draft")
            st_style = "green" if st == "published" else "yellow"
            table.add_row(w.get("id"), w.get("name", ""), str(len(w.get("nodes", []))), f"[{st_style}]{st}[/{st_style}]", str(w.get("version", 1)))
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("create")
def create_workflow(
    from_file: Path = typer.Option(..., "--from", help="YAML workflow definition"),
):
    """Create a workflow from YAML file."""
    if not from_file.exists():
        console.print(f"[red]Error:[/red] File not found: {from_file}")
        raise typer.Exit(1)
    wf = yaml.safe_load(from_file.read_text())
    try:
        gateway_post("/build/workflows", wf)
        console.print(f"[green]✓[/green] Workflow created: {wf.get('id', '?')}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("publish")
def publish_workflow(workflow_id: str = typer.Argument(help="Workflow ID")):
    """Publish a workflow."""
    try:
        gateway_post(f"/build/workflows/{workflow_id}/publish")
        console.print(f"[green]✓[/green] Published: {workflow_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("trigger")
def trigger_workflow(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Input message"),
):
    """Trigger a workflow execution."""
    payload = {"input": {"message": input}} if input else {"input": {}}
    try:
        data = gateway_post(f"/workflows/{workflow_id}/trigger", payload)
        console.print(f"[green]✓[/green] Triggered: {workflow_id}")
        if data.get("run_id"):
            console.print(f"  Run ID: {data['run_id']}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("runs")
def list_runs(
    workflow_id: Optional[str] = typer.Option(None, "--workflow", "-w"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
):
    """List workflow runs."""
    try:
        params = {}
        if workflow_id:
            params["workflow_id"] = workflow_id
        if status:
            params["status"] = status
        data = gateway_get("/workflows/runs", params=params)
        runs = data.get("runs", [])
        if not runs:
            console.print("[dim]No runs.[/dim]")
            return
        table = Table(title="Workflow Runs")
        table.add_column("Run ID", style="bold")
        table.add_column("Workflow")
        table.add_column("Status")
        table.add_column("Trigger")
        for r in runs:
            st = r.get("status", "?")
            st_style = "green" if st == "completed" else "yellow" if "waiting" in st else "red" if st == "failed" else "dim"
            trigger = r.get("trigger", {})
            tby = trigger.get("triggered_by", "?") if isinstance(trigger, dict) else "?"
            table.add_row(r.get("id", ""), r.get("workflow_id", ""), f"[{st_style}]{st}[/{st_style}]", tby)
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("delete")
def delete_workflow(workflow_id: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a workflow."""
    if not confirm:
        typer.confirm(f"Delete workflow '{workflow_id}'?", abort=True)
    try:
        gateway_delete(f"/build/workflows/{workflow_id}")
        console.print(f"[green]✓[/green] Deleted: {workflow_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
