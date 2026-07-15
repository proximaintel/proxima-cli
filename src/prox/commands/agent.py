"""prox agent — manage agents on the platform."""

import json
import subprocess
import tarfile
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from ..api import gateway_get, gateway_post, gateway_put, gateway_delete, APIError
from ..config import get_value

app = typer.Typer(help="Manage platform agents.")
console = Console()


@app.command("list")
def list_agents(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (active/draft)"),
):
    """List all agents on the platform."""
    try:
        params = {}
        if domain:
            params["domain"] = domain
        if status:
            params["status"] = status
        data = gateway_get("/build/agents", params=params)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    agents = data.get("agents", [])
    if not agents:
        console.print("[dim]No agents found.[/dim]")
        return

    table = Table(title=f"Agents ({len(agents)})")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Domain")
    table.add_column("Status")
    table.add_column("Version", justify="right")

    for a in agents:
        st = a.get("status", "draft")
        st_style = "green" if st == "active" else "yellow" if st == "draft" else "dim"
        table.add_row(
            a.get("id", ""),
            a.get("name", ""),
            a.get("domain", ""),
            f"[{st_style}]{st}[/{st_style}]",
            str(a.get("version", 1)),
        )

    console.print(table)


@app.command("get")
def get_agent(agent_id: str = typer.Argument(help="Agent ID")):
    """Get agent details."""
    try:
        data = gateway_get(f"/build/agents/{agent_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    agent = data.get("agent", data)
    console.print(f"\n[bold]{agent.get('name', agent_id)}[/bold]")
    console.print(f"  ID:          {agent.get('id')}")
    console.print(f"  Codename:    {agent.get('codename', '—')}")
    console.print(f"  Domain:      {agent.get('domain', '—')}")
    console.print(f"  Role:        {agent.get('role', 'agent')}")
    console.print(f"  Status:      {agent.get('status', '—')}")
    console.print(f"  Version:     {agent.get('version', 1)}")
    console.print(f"  Model:       {agent.get('llm', {}).get('model', '—')}")
    if agent.get("toolboxes"):
        console.print(f"  Toolboxes:   {', '.join(agent['toolboxes'])}")
    if agent.get("knowledge_bases"):
        console.print(f"  Knowledge:   {', '.join(agent['knowledge_bases'])}")
    console.print()


@app.command("create")
def create_agent(
    name: str = typer.Option(None, "--name", "-n", help="Agent name"),
    codename: str = typer.Option(None, "--codename", help="Agent codename"),
    domain: str = typer.Option(None, "--domain", "-d", help="Domain"),
    role: str = typer.Option("agent", "--role", help="Role: agent or orchestrator"),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Create from agent.yaml file"),
):
    """Create a new agent."""
    if from_file:
        if not from_file.exists():
            console.print(f"[red]Error:[/red] File not found: {from_file}")
            raise typer.Exit(1)
        config = yaml.safe_load(from_file.read_text())
    else:
        if not name:
            console.print("[red]Error:[/red] Provide --name or --from")
            raise typer.Exit(1)
        agent_id = name.lower().replace(" ", "-").replace("_", "-")
        config = {"id": agent_id, "name": name, "codename": codename or "", "domain": domain or "", "role": role}

    try:
        data = gateway_post("/build/agents", config)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Agent created: {config.get('id', config.get('name'))}")


@app.command("update")
def update_agent(
    agent_id: str = typer.Argument(help="Agent ID"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="System prompt"),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID"),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Update from agent.yaml"),
    publish: bool = typer.Option(False, "--publish", "-p", help="Auto-publish after update"),
):
    """Update an agent's configuration (creates a new draft version)."""
    if from_file:
        if not from_file.exists():
            console.print(f"[red]Error:[/red] File not found: {from_file}")
            raise typer.Exit(1)
        config = yaml.safe_load(from_file.read_text())
    else:
        config = {}
        if prompt:
            config["system_prompt"] = prompt
        if model:
            config["llm"] = {"model": model}
        if not config:
            console.print("[red]Error:[/red] Provide --prompt, --model, or --from")
            raise typer.Exit(1)

    try:
        data = gateway_put(f"/build/agents/{agent_id}", config)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    version = data.get("version", "?")
    console.print(f"[green]✓[/green] Draft created: {agent_id} (v{version})")

    if publish or typer.confirm("Publish now?", default=True):
        try:
            gateway_post(f"/build/agents/{agent_id}/publish")
            console.print(f"[green]✓[/green] Published: {agent_id} v{version}")
        except APIError as e:
            console.print(f"[red]Error:[/red] Publish failed: {e.detail}")
            raise typer.Exit(1)
    else:
        console.print(f"[dim]Draft saved. Publish with:[/dim] prox agent publish {agent_id}")


@app.command("publish")
def publish_agent(agent_id: str = typer.Argument(help="Agent ID to publish")):
    """Publish an agent (draft → active)."""
    try:
        gateway_post(f"/build/agents/{agent_id}/publish")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Published: {agent_id}")


@app.command("delete")
def delete_agent(
    agent_id: str = typer.Argument(help="Agent ID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete an agent."""
    if not confirm:
        typer.confirm(f"Delete agent '{agent_id}'? This cannot be undone", abort=True)

    try:
        gateway_delete(f"/build/agents/{agent_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Deleted: {agent_id}")


@app.command("deploy")
def deploy_agent(
    from_path: Path = typer.Option(..., "--from", help="Path to agent package directory"),
):
    """Full agent deploy: build toolbox → register → configure → publish.

    Expects directory structure:
      agent.yaml, toolbox/, workspace.json, knowledge.yaml, ontology.yaml, data/synthetic/
    """
    if not from_path.exists():
        console.print(f"[red]Error:[/red] Path not found: {from_path}")
        raise typer.Exit(1)

    agent_yaml = from_path / "agent.yaml"
    if not agent_yaml.exists():
        console.print(f"[red]Error:[/red] No agent.yaml found in {from_path}")
        raise typer.Exit(1)

    config = yaml.safe_load(agent_yaml.read_text())
    agent_id = config["id"]
    console.print(f"\n[bold]Deploying:[/bold] {config.get('name', agent_id)} ({agent_id})\n")

    # Step 1: Build and push toolbox (if exists)
    toolbox_dir = from_path / "toolbox"
    if toolbox_dir.exists() and (toolbox_dir / "Dockerfile").exists():
        _deploy_toolbox(agent_id, toolbox_dir, config)

    # Step 2: Upload knowledge data (if exists)
    knowledge_yaml = from_path / "knowledge.yaml"
    if knowledge_yaml.exists():
        _deploy_knowledge(agent_id, knowledge_yaml, from_path)

    # Step 2b: Deploy ontology (if exists)
    ontology_yaml = from_path / "ontology.yaml"
    if ontology_yaml.exists():
        console.print("  [bold]2b.[/bold] Deploying ontology...")
        try:
            ont_data = yaml.safe_load(ontology_yaml.read_text())
            ont_id = ont_data.get("id", f"{agent_id}-ontology")
            gateway_post("/build/ontology", ont_data)
            # Connect ontology to agent config
            config["ontology"] = {"id": ont_id}
            console.print(f"     [green]\u2713[/green] Ontology deployed: {ont_id}")
        except APIError:
            # May already exist — try update
            try:
                gateway_put(f"/build/ontology/{ont_data.get('id', '')}", ont_data)
                config["ontology"] = {"id": ont_data.get('id', '')}
                console.print(f"     [green]\u2713[/green] Ontology updated: {ont_data.get('id', '')}")
            except APIError as e:
                console.print(f"     [yellow]\u26a0[/yellow] Ontology: {e.detail}")

    # Step 3: Create/update agent in registry
    console.print("  [bold]3.[/bold] Registering agent...")
    try:
        gateway_put(f"/build/agents/{agent_id}", config)
        console.print("     [green]✓[/green] Agent registered")
    except APIError as e:
        console.print(f"     [red]✗[/red] {e.detail}")
        raise typer.Exit(1)

    # Step 4: Push workspace (if exists)
    workspace_json = from_path / "workspace.json"
    if workspace_json.exists():
        console.print("  [bold]4.[/bold] Pushing workspace...")
        try:
            ws = json.loads(workspace_json.read_text())
            gateway_put(f"/workspaces/{agent_id}", ws)
            console.print("     [green]✓[/green] Workspace pushed")
        except APIError as e:
            console.print(f"     [yellow]⚠[/yellow] Workspace push failed: {e.detail}")

    # Step 5: Publish
    console.print("  [bold]5.[/bold] Publishing...")
    try:
        gateway_post(f"/build/agents/{agent_id}/publish")
        console.print("     [green]✓[/green] Published (status: active)")
    except APIError as e:
        console.print(f"     [yellow]⚠[/yellow] Publish failed: {e.detail}")

    # Step 6: Health check
    console.print("  [bold]6.[/bold] Health check...")
    try:
        health = gateway_get(f"/agents/{agent_id}/health")
        console.print(f"     [green]✓[/green] Healthy")
    except APIError:
        console.print("     [yellow]⚠[/yellow] Health check unavailable")

    console.print(f"\n[green]✓ Deploy complete:[/green] {agent_id}\n")


def _deploy_toolbox(agent_id: str, toolbox_dir: Path, config: dict):
    """Build Docker image, push to registry, register toolbox."""
    registry = get_value("registry")
    if not registry:
        console.print("  [bold]1.[/bold] Toolbox — [yellow]skipped[/yellow] (no registry configured)")
        return

    image = f"{registry}/{agent_id}-toolbox:latest"
    console.print(f"  [bold]1.[/bold] Building toolbox → {image}")

    # Build
    result = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64", "-t", image, "."],
        cwd=toolbox_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print(f"     [red]✗[/red] Docker build failed:\n{result.stderr[:300]}")
        raise typer.Exit(1)
    console.print("     [green]✓[/green] Image built")

    # Push
    result = subprocess.run(
        ["docker", "push", image],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print(f"     [red]✗[/red] Docker push failed:\n{result.stderr[:300]}")
        raise typer.Exit(1)
    console.print("     [green]✓[/green] Image pushed")

    # Register toolbox with gateway
    toolbox_id = config.get("toolboxes", [None])[0] or f"{agent_id}-toolbox"
    console.print(f"  [bold]2.[/bold] Registering toolbox: {toolbox_id}")
    try:
        gateway_post("/build/toolboxes", {
            "id": toolbox_id,
            "name": f"{config.get('name', agent_id)} Toolbox",
            "endpoint": f"http://{agent_id}:8001",
            "type": "openapi",
        })
        # Discover tools
        gateway_post("/build/toolboxes/discover", {"toolbox_id": toolbox_id})
        console.print("     [green]✓[/green] Toolbox registered + tools discovered")
    except APIError as e:
        console.print(f"     [yellow]⚠[/yellow] Toolbox registration: {e.detail}")


def _deploy_knowledge(agent_id: str, knowledge_yaml: Path, base_path: Path):
    """Create knowledge sources and bases from knowledge.yaml."""
    console.print("  [bold]2b.[/bold] Setting up knowledge...")
    kconfig = yaml.safe_load(knowledge_yaml.read_text())

    # Create sources
    for source in kconfig.get("sources", []):
        try:
            gateway_post("/build/knowledge/sources", source)
            console.print(f"     [green]✓[/green] Source: {source.get('id', '?')}")
        except APIError:
            pass  # May already exist

    # Create bases
    for base in kconfig.get("bases", []):
        try:
            gateway_post("/build/knowledge/bases", base)
            console.print(f"     [green]✓[/green] Base: {base.get('id', '?')}")
        except APIError:
            pass  # May already exist

    # Upload synthetic data if present
    data_dir = base_path / "data" / "synthetic"
    if data_dir.exists():
        parquets = list(data_dir.glob("*.parquet"))
        if parquets:
            console.print(f"     [dim]({len(parquets)} parquet files — upload via knowledge source config)[/dim]")
