"""prox governance — audit logs and platform metrics."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, APIError

app = typer.Typer(help="View governance logs and stats.")
console = Console()


@app.command("logs")
def logs(
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """View audit logs."""
    try:
        params = {"limit": limit}
        if domain:
            params["domain"] = domain
        data = gateway_get("/governance/logs", params=params)
        entries = data.get("logs", data.get("entries", []))
        if not entries:
            console.print("[dim]No logs.[/dim]")
            return
        table = Table(title=f"Governance Logs (last {limit})")
        table.add_column("Time", style="dim")
        table.add_column("Type")
        table.add_column("Agent")
        table.add_column("User")
        table.add_column("Tokens", justify="right")
        for e in entries[:limit]:
            table.add_row(
                e.get("timestamp", "")[:19],
                e.get("type", "query"),
                e.get("agent_id", ""),
                e.get("user", ""),
                str(e.get("tokens_used", "")),
            )
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("stats")
def stats(domain: Optional[str] = typer.Option(None, "--domain", "-d")):
    """View platform stats."""
    try:
        params = {"domain": domain} if domain else {}
        data = gateway_get("/governance/stats", params=params)
        console.print(f"\n  [bold]Platform Stats[/bold]{'  (' + domain + ')' if domain else ''}\n")
        console.print(f"  Total queries:  {data.get('total_queries', 0)}")
        console.print(f"  Total tokens:   {data.get('total_tokens', 0):,}")
        console.print(f"  Total cost:     ${data.get('total_cost', 0):.2f}")
        console.print(f"  Avg duration:   {data.get('avg_duration_ms', 0):.0f}ms")
        console.print(f"  Agents active:  {data.get('agents_active', 0)}")
        console.print()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
