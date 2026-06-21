"""prox catalog — browse, pull, and push agent packages."""

import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..api import catalog_get, catalog_post, catalog_download, APIError
from ..config import PACKAGES_DIR, get_license_key, get_master_key

app = typer.Typer(help="Browse and manage the Proxima Agent Catalog.")
console = Console()


@app.command("list")
def list_agents(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """List all agents in the catalog."""
    try:
        params = {}
        if domain:
            params["domain"] = domain
        data = catalog_get("/catalog/agents", params=params)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    agents = data.get("agents", [])
    if not agents:
        console.print("[dim]No agents found.[/dim]")
        return

    if format == "json":
        import json
        console.print(json.dumps(agents, indent=2))
        return

    # Check license to mark available agents
    licensed_ids = set()
    try:
        lic = catalog_get("/catalog/license")
        licensed_ids = set(lic.get("agents", []))
    except APIError:
        pass  # No license configured — show all without marks

    table = Table(title=f"Proxima Catalog ({len(agents)} agents)")
    table.add_column("Agent", style="bold")
    table.add_column("Codename", style="cyan")
    table.add_column("Domain")
    table.add_column("Tools", justify="right")
    table.add_column("Version")
    table.add_column("Access", justify="center")

    for agent in agents:
        aid = agent["id"]
        access = "✓" if aid in licensed_ids or get_master_key() else "○"
        access_style = "green" if access == "✓" else "dim"
        table.add_row(
            agent.get("name", aid),
            agent.get("codename", ""),
            agent.get("domain", ""),
            str(agent.get("tools", 0)),
            agent.get("latest_version", "—"),
            f"[{access_style}]{access}[/{access_style}]",
        )

    console.print(table)
    if licensed_ids:
        console.print(f"\n[green]✓[/green] = licensed  [dim]○[/dim] = contact Proxima")


@app.command("show")
def show_agent(agent_id: str = typer.Argument(help="Agent ID")):
    """Show detailed information about a catalog agent."""
    try:
        data = catalog_get(f"/catalog/agents/{agent_id}")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"\n[bold]{data.get('name', agent_id)}[/bold] ({data.get('codename', '')})")
    console.print(f"[dim]{data.get('description', '')}[/dim]\n")
    console.print(f"  Domain:   {data.get('domain', '—')}")
    console.print(f"  Tools:    {data.get('tools', 0)}")
    console.print(f"  Version:  {data.get('latest_version', '—')}")
    console.print(f"  Updated:  {data.get('updated_at', '—')}")

    if data.get("tool_names"):
        console.print(f"\n  [bold]Tools:[/bold]")
        for t in data["tool_names"]:
            console.print(f"    • {t}")

    if data.get("industries"):
        console.print(f"\n  [bold]Industries:[/bold] {', '.join(data['industries'])}")
    if data.get("functions"):
        console.print(f"  [bold]Functions:[/bold] {', '.join(data['functions'])}")
    console.print()


@app.command("pull")
def pull_agent(
    agent_id: str = typer.Argument(help="Agent ID to pull"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Specific version (default: latest)"),
):
    """Pull an agent package from the catalog."""
    if not get_license_key() and not get_master_key():
        console.print("[red]Error:[/red] No license key configured. Run: prox login --license-key <key>")
        raise typer.Exit(1)

    console.print(f"[bold]Pulling[/bold] {agent_id}" + (f"@{version}" if version else " (latest)") + "...")

    # Get download URL / validate access
    try:
        params = {"version": version} if version else {}
        meta = catalog_get(f"/catalog/agents/{agent_id}", params=params)
    except APIError as e:
        if e.status == 403:
            console.print(f"[red]Access denied:[/red] '{agent_id}' is not in your license. Contact Proxima to upgrade.")
        else:
            console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    actual_version = version or meta.get("latest_version", "latest")
    dest_dir = PACKAGES_DIR / agent_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    tarball = dest_dir / f"{agent_id}-{actual_version}.tar.gz"

    try:
        pull_path = f"/catalog/agents/{agent_id}/pull"
        if version:
            pull_path += f"?version={version}"
        catalog_download(pull_path, str(tarball))
    except APIError as e:
        console.print(f"[red]Download failed:[/red] {e.detail}")
        raise typer.Exit(1)

    # Extract
    extract_dir = dest_dir / actual_version
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as tar:
        tar.extractall(path=extract_dir)

    console.print(f"[green]✓[/green] Pulled {agent_id}@{actual_version} → {extract_dir}")
    console.print(f"\n  Deploy with: [bold]prox agent deploy --from {extract_dir}[/bold]")


@app.command("push")
def push_agent(
    from_path: Path = typer.Option(..., "--from", help="Path to agent directory"),
    version: str = typer.Option(..., "--version", "-v", help="Version to publish"),
):
    """Push an agent package to the catalog (Proxima team only)."""
    if not get_master_key():
        console.print("[red]Error:[/red] Master key required. Run: prox login --master-key <key>")
        raise typer.Exit(1)

    if not from_path.exists():
        console.print(f"[red]Error:[/red] Path not found: {from_path}")
        raise typer.Exit(1)

    # Read manifest or agent.yaml for the agent ID
    manifest = from_path / "manifest.json"
    agent_yaml = from_path / "agent.yaml"
    if manifest.exists():
        import json
        meta = json.loads(manifest.read_text())
        agent_id = meta["id"]
    elif agent_yaml.exists():
        import yaml
        meta = yaml.safe_load(agent_yaml.read_text())
        agent_id = meta["id"]
    else:
        console.print("[red]Error:[/red] No manifest.json or agent.yaml found in source directory.")
        raise typer.Exit(1)

    console.print(f"[bold]Packaging[/bold] {agent_id}@{version}...")

    # Create tarball
    tarball_path = Path(tempfile.mktemp(suffix=".tar.gz"))
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(from_path, arcname=".")

    size_mb = tarball_path.stat().st_size / (1024 * 1024)
    console.print(f"  Package size: {size_mb:.1f} MB")
    console.print(f"[bold]Pushing[/bold] to catalog...")

    # Upload
    try:
        import httpx
        from ..config import get_value
        catalog_url = (get_value("catalog") or "https://catalog.proximaintel.com").rstrip("/")
        with open(tarball_path, "rb") as f:
            r = httpx.post(
                f"{catalog_url}/catalog/agents/{agent_id}/push?version={version}",
                headers={"X-Master-Key": get_master_key()},
                content=f.read(),
                timeout=300,
            )
        if r.status_code >= 400:
            console.print(f"[red]Push failed:[/red] {r.text[:300]}")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Push failed:[/red] {e}")
        raise typer.Exit(1)
    finally:
        tarball_path.unlink(missing_ok=True)

    console.print(f"[green]✓[/green] Pushed {agent_id}@{version} to catalog")


@app.command("license")
def check_license():
    """Check current license entitlements."""
    if not get_license_key() and not get_master_key():
        console.print("[yellow]No license key configured.[/yellow]")
        console.print("  Run: prox login --license-key <key>")
        return

    if get_master_key():
        console.print("[bold green]Master key active[/bold green] — full catalog access")
        return

    try:
        data = catalog_get("/catalog/license")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"\n[bold]License:[/bold] {data.get('client_id', '—')}")
    console.print(f"  Tier:     {data.get('tier', '—')}")
    console.print(f"  Expires:  {data.get('expires', '—')}")
    console.print(f"  Valid:    {'[green]Yes[/green]' if data.get('valid') else '[red]No[/red]'}")
    console.print(f"\n  [bold]Licensed agents ({len(data.get('agents', []))}):[/bold]")
    for a in data.get("agents", []):
        console.print(f"    • {a}")
    console.print()


@app.command("deploy")
def deploy_from_catalog(
    agent_id: str = typer.Argument(help="Agent ID to deploy from catalog"),
    version: str = typer.Option("latest", "--version", "-v", help="Version to deploy"),
    domain: str = typer.Option("", "--domain", "-d", help="Override domain assignment"),
):
    """Deploy an agent from catalog to the platform (server-side).

    Triggers async deployment — the platform handles container provisioning,
    registration, and configuration. Poll status with: prox catalog status <agent_id>
    """
    from ..api import gateway_post, gateway_get, APIError
    import time as _time

    console.print(f"\n[bold]Deploying from catalog:[/bold] {agent_id} v{version}\n")

    try:
        result = gateway_post(f"/catalog/deploy/{agent_id}", {
            "version": version,
            "domain": domain,
        })
        deployment_id = result.get("deployment_id")
        console.print(f"  [green]✓[/green] Deployment triggered: {deployment_id}")
        console.print(f"  Polling status...\n")

        # Poll until complete or failed
        for _ in range(120):  # 4 minutes max
            _time.sleep(2)
            try:
                status = gateway_get(f"/catalog/deploy/{agent_id}/status")
                step = status.get("step", 0)
                total = status.get("total_steps", 14)
                state = status.get("status", "unknown")
                message = status.get("message", "")

                console.print(f"  [{step}/{total}] {state}: {message}", end="\r")

                if state in ("deployed", "upgraded"):
                    console.print(f"\n\n  [green]✓[/green] {message}")
                    console.print(f"  Agent deployed as draft. Publish with: prox agent publish {agent_id}")
                    return
                elif state == "failed":
                    console.print(f"\n\n  [red]✗[/red] Deployment failed: {message}")
                    raise typer.Exit(1)
            except APIError:
                pass

        console.print(f"\n\n  [yellow]⚠[/yellow] Deployment timed out. Check: prox catalog status {agent_id}")

    except APIError as e:
        console.print(f"  [red]✗[/red] {e.detail}")
        raise typer.Exit(1)


@app.command("status")
def deployment_status(
    agent_id: str = typer.Argument(help="Agent ID to check deployment status"),
):
    """Check deployment status for an agent."""
    from ..api import gateway_get, APIError

    try:
        status = gateway_get(f"/catalog/deploy/{agent_id}/status")
        state = status.get("status", "unknown")
        step = status.get("step", 0)
        total = status.get("total_steps", 14)
        message = status.get("message", "")
        started = status.get("started_at", "")

        console.print(f"\n  Agent:   {agent_id}")
        console.print(f"  Status:  {state}")
        console.print(f"  Step:    {step}/{total}")
        console.print(f"  Message: {message}")
        if started:
            console.print(f"  Started: {started}")
        console.print()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)
