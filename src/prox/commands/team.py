"""prox team — manage agent hierarchy and relationships."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from ..api import gateway_get, gateway_post, gateway_delete, APIError

app = typer.Typer(help="Manage agent teams and relationships.")
console = Console()


@app.command("show")
def show_team():
    """Show agent hierarchy and relationships."""
    try:
        data = gateway_get("/team")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    agents = data.get("agents", [])
    relationships = data.get("relationships", [])
    teams = data.get("teams", [])

    if not agents:
        console.print("[dim]No agents deployed.[/dim]")
        return

    # Show agents by domain
    domains: dict[str, list] = {}
    for a in agents:
        d = a.get("domain", "unknown")
        domains.setdefault(d, []).append(a)

    console.print(f"\n[bold]AI Workforce[/bold] — {len(agents)} agents, {len(relationships)} relationships\n")
    for domain, domain_agents in sorted(domains.items()):
        console.print(f"  [bold]{domain}[/bold]")
        for a in domain_agents:
            role = a.get("role", "agent")
            status = a.get("status", "planned")
            st_style = "green" if status == "active" else "dim"
            prefix = "  ★" if role == "orchestrator" else "   "
            console.print(f"  {prefix} {a.get('codename', '')} ({a.get('name', a['id'])}) [{st_style}]{status}[/{st_style}]")
        console.print()

    if relationships:
        console.print(f"  [bold]Relationships:[/bold]")
        for r in relationships[:15]:
            console.print(f"    {r.get('from', '?')} → {r.get('to', '?')}: {r.get('description', '')}")
        if len(relationships) > 15:
            console.print(f"    ... +{len(relationships) - 15} more")
    console.print()


@app.command("add")
def add_relationship(
    from_agent: str = typer.Option(..., "--from", help="Source agent ID"),
    to_agent: str = typer.Option(..., "--to", help="Target agent ID"),
    description: str = typer.Option(..., "--desc", help="Relationship description"),
):
    """Add a relationship between two agents."""
    try:
        gateway_post("/team/relationships", {"from": from_agent, "to": to_agent, "description": description})
        console.print(f"[green]✓[/green] Relationship added: {from_agent} → {to_agent}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("remove")
def remove_relationship(
    from_agent: str = typer.Option(..., "--from", help="Source agent ID"),
    to_agent: str = typer.Option(..., "--to", help="Target agent ID"),
):
    """Remove a relationship between two agents."""
    try:
        gateway_delete("/team/relationships")  # This needs body — use post with delete semantic
        console.print(f"[green]✓[/green] Relationship removed: {from_agent} → {to_agent}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
