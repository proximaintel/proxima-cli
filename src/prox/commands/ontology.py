"""prox ontology — manage ontologies on the platform."""

from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from ..api import gateway_get, gateway_post, gateway_put, gateway_delete, APIError

app = typer.Typer(help="Manage ontologies.")
console = Console()


@app.command("list")
def list_ontologies():
    """List all ontologies on the platform."""
    try:
        data = gateway_get("/build/ontology")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    ontologies = data.get("ontologies", [])
    if not ontologies:
        console.print("[dim]No ontologies.[/dim]")
        return

    table = Table(title=f"Ontologies ({len(ontologies)})")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Entities", justify="right")
    table.add_column("Actions", justify="right")
    table.add_column("Version")

    for o in ontologies:
        table.add_row(o.get("id"), o.get("name", ""), str(o.get("entities", 0)), str(o.get("actions", 0)), o.get("version", "—"))

    console.print(table)


@app.command("show")
def show_ontology(ontology_id: str = typer.Argument(help="Ontology ID")):
    """Show ontology details."""
    try:
        data = gateway_get(f"/build/ontology/{ontology_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    o = data.get("ontology", {})
    console.print(f"\n[bold]{o.get('name', ontology_id)}[/bold] (v{o.get('version', '?')})")
    console.print(f"[dim]{o.get('description', '')}[/dim]\n")

    entities = o.get("entities", {})
    relationships = o.get("relationships", [])
    actions = o.get("actions", {})
    events = o.get("events", [])

    console.print(f"  Entities:       {len(entities)}")
    console.print(f"  Relationships:  {len(relationships)}")
    console.print(f"  Actions:        {len(actions)}")
    console.print(f"  Events:         {len(events)}")
    console.print()

    if entities:
        console.print("  [bold]Entities:[/bold]")
        for name, edef in entities.items():
            props = len(edef.get("properties", {}))
            console.print(f"    • {name} ({props} properties)")
    if actions:
        console.print(f"\n  [bold]Actions:[/bold]")
        for aname, adef in actions.items():
            console.print(f"    • {aname} → {adef.get('entity', '?')}")
    console.print()


@app.command("create")
def create_ontology(
    from_file: Path = typer.Option(..., "--from", help="YAML ontology definition file"),
):
    """Create an ontology from a YAML file."""
    if not from_file.exists():
        console.print(f"[red]Error:[/red] File not found: {from_file}")
        raise typer.Exit(1)

    data = yaml.safe_load(from_file.read_text())
    if not data.get("id"):
        console.print("[red]Error:[/red] Ontology YAML must have an 'id' field")
        raise typer.Exit(1)

    try:
        gateway_post("/build/ontology", data)
        console.print(f"[green]✓[/green] Ontology created: {data['id']}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("update")
def update_ontology(
    ontology_id: str = typer.Argument(help="Ontology ID"),
    from_file: Path = typer.Option(..., "--from", help="YAML ontology definition file"),
):
    """Update an existing ontology from a YAML file."""
    if not from_file.exists():
        console.print(f"[red]Error:[/red] File not found: {from_file}")
        raise typer.Exit(1)

    data = yaml.safe_load(from_file.read_text())
    data["id"] = ontology_id

    try:
        gateway_put(f"/build/ontology/{ontology_id}", data)
        console.print(f"[green]✓[/green] Ontology updated: {ontology_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("validate")
def validate_ontology_cmd(
    from_file: Path = typer.Option(..., "--from", help="YAML ontology file to validate"),
):
    """Validate an ontology YAML file without creating it."""
    if not from_file.exists():
        console.print(f"[red]Error:[/red] File not found: {from_file}")
        raise typer.Exit(1)

    data = yaml.safe_load(from_file.read_text())

    # Import the validator
    import sys
    from pathlib import Path as P
    platform_path = str(P(__file__).resolve().parent.parent.parent.parent.parent)
    sys.path.insert(0, platform_path)
    try:
        from ontology import validate_ontology
        errors = validate_ontology(data)
        if errors:
            console.print(f"[red]✗ Validation failed ({len(errors)} errors):[/red]")
            for err in errors:
                console.print(f"  • {err}")
            raise typer.Exit(1)
        else:
            entities = len(data.get("entities", {}))
            actions = len(data.get("actions", {}))
            console.print(f"[green]✓[/green] Valid ontology: {data.get('id', '?')} ({entities} entities, {actions} actions)")
    except ImportError:
        # Fallback: basic validation
        if not data.get("id"):
            console.print("[red]✗[/red] Missing 'id' field")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] Basic validation passed: {data.get('id', '?')}")


@app.command("publish")
def publish_ontology(ontology_id: str = typer.Argument(help="Ontology ID to publish")):
    """Publish an ontology (creates immutable version)."""
    try:
        data = gateway_post(f"/build/ontology/{ontology_id}/publish")
        console.print(f"[green]✓[/green] Published: {ontology_id} → v{data.get('version', '?')}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("versions")
def list_versions(ontology_id: str = typer.Argument(help="Ontology ID")):
    """List published versions of an ontology."""
    try:
        data = gateway_get(f"/build/ontology/{ontology_id}/versions")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    versions = data.get("versions", [])
    if not versions:
        console.print("[dim]No published versions yet.[/dim]")
        return

    table = Table(title=f"Versions — {ontology_id}")
    table.add_column("Version", style="bold")
    table.add_column("Entities", justify="right")
    table.add_column("Published")

    for v in versions:
        table.add_row(f"v{v.get('version', '?')}", str(v.get("entities", 0)), v.get("published_at", "—"))

    console.print(table)


@app.command("delete")
def delete_ontology(
    ontology_id: str = typer.Argument(help="Ontology ID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete an ontology."""
    if not confirm:
        typer.confirm(f"Delete ontology '{ontology_id}'? This cannot be undone", abort=True)

    try:
        gateway_delete(f"/build/ontology/{ontology_id}")
        console.print(f"[green]✓[/green] Deleted: {ontology_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
