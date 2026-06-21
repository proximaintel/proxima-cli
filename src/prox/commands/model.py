"""prox model — manage LLM model connections."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, gateway_post, gateway_delete, APIError

app = typer.Typer(help="Manage LLM models.")
console = Console()


@app.command("list")
def list_models():
    """List deployed models."""
    try:
        data = gateway_get("/build/models")
        models = data.get("models", [])
        if not models:
            console.print("[dim]No models.[/dim]")
            return
        table = Table(title="Models")
        table.add_column("ID", style="bold")
        table.add_column("Provider")
        table.add_column("Model")
        table.add_column("Status")
        for m in models:
            st = m.get("status", "unknown")
            st_style = "green" if st == "active" else "yellow"
            table.add_row(m.get("id"), m.get("provider", ""), m.get("model", ""), f"[{st_style}]{st}[/{st_style}]")
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("deploy")
def deploy_model(
    id: str = typer.Option(..., "--id"),
    provider: str = typer.Option(..., "--provider", help="openai, anthropic, bedrock, watsonx, ollama"),
    model: str = typer.Option(..., "--model", help="Model name (e.g. gpt-4.1-mini)"),
    endpoint_secret: Optional[str] = typer.Option(None, "--endpoint-secret"),
    key_secret: Optional[str] = typer.Option(None, "--key-secret"),
):
    """Deploy a model connection."""
    payload = {"id": id, "provider": provider, "model": model}
    if endpoint_secret:
        payload["endpoint_secret"] = endpoint_secret
    if key_secret:
        payload["key_secret"] = key_secret
    try:
        gateway_post("/build/models", payload)
        console.print(f"[green]✓[/green] Model deployed: {id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("delete")
def delete_model(model_id: str = typer.Argument(), confirm: bool = typer.Option(False, "--yes", "-y")):
    """Delete a model."""
    if not confirm:
        typer.confirm(f"Delete model '{model_id}'?", abort=True)
    try:
        gateway_delete(f"/build/models/{model_id}")
        console.print(f"[green]✓[/green] Deleted: {model_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
