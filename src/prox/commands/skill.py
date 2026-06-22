"""prox skill — manage skills (prompt templates)."""

import typer
from rich.console import Console
from rich.table import Table

from ..api import gateway_get, gateway_delete, APIError

app = typer.Typer(help="Manage skills.")
console = Console()


@app.command("list")
def list_skills():
    """List all skills on the platform."""
    try:
        data = gateway_get("/build/skills")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    skills = data.get("skills", [])
    if not skills:
        console.print("[dim]No skills registered.[/dim]")
        return

    table = Table(title=f"Skills ({len(skills)})")
    table.add_column("ID", style="bold")
    table.add_column("Version", justify="right")
    table.add_column("Description")

    for s in skills:
        table.add_row(
            s.get("id", s.get("name", "")),
            str(s.get("version", "")),
            s.get("description", "")[:60],
        )

    console.print(table)


@app.command("delete")
def delete_skill(
    skill_id: str = typer.Argument(help="Skill ID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y"),
):
    """Delete a skill."""
    if not confirm:
        typer.confirm(f"Delete skill '{skill_id}'?", abort=True)
    try:
        gateway_delete(f"/build/skills/{skill_id}")
        console.print(f"[green]✓[/green] Deleted: {skill_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("delete-all")
def delete_all_skills(
    confirm: bool = typer.Option(False, "--yes", "-y"),
):
    """Delete all skills from the platform."""
    if not confirm:
        typer.confirm("Delete ALL skills?", abort=True)
    try:
        data = gateway_get("/build/skills")
        skills = data.get("skills", [])
        for s in skills:
            sid = s.get("id", s.get("name", ""))
            if sid:
                gateway_delete(f"/build/skills/{sid}")
                console.print(f"  [green]✓[/green] {sid}")
        console.print(f"\n[green]✓[/green] Deleted {len(skills)} skills")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
