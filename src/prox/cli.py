"""Proxima Platform CLI — entry point."""

import typer
from rich.console import Console

from . import __version__, auth, config
from .commands import catalog, agent, toolbox, knowledge, secret, model, routine, workflow, governance, platform, ontology, team

def version_callback(value: bool):
    if value:
        from . import __version__
        print(f"prox {__version__}")
        raise typer.Exit()

app = typer.Typer(
    name="prox",
    help="Proxima AIP CLI",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

@app.callback()
def main(version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version")):
    pass
console = Console()

# --- Command groups ---
app.add_typer(catalog.app, name="catalog")
app.add_typer(agent.app, name="agent")
app.add_typer(toolbox.app, name="toolbox")
app.add_typer(knowledge.app, name="knowledge")
app.add_typer(ontology.app, name="ontology")
app.add_typer(secret.app, name="secret")
app.add_typer(model.app, name="model")
app.add_typer(routine.app, name="routine")
app.add_typer(workflow.app, name="workflow")
app.add_typer(governance.app, name="governance")
app.add_typer(platform.app, name="platform")
app.add_typer(team.app, name="team")


# --- Top-level commands ---

@app.command()
def login(
    api_key: str = typer.Option(None, "--api-key", help="Platform API key"),
    license_key: str = typer.Option(None, "--license-key", help="Catalog license key"),
    master_key: str = typer.Option(None, "--master-key", help="Catalog master key (Proxima only)"),
):
    """Authenticate with the platform and/or catalog.

    With no flags: opens browser for SSO login.
    """
    if not api_key and not license_key and not master_key:
        # SSO flow
        console.print("Opening browser for SSO login...")
        try:
            auth.login_sso()
            console.print("[green]✓[/green] Authenticated via SSO")
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        return
    if api_key:
        auth.login_api_key(api_key)
        console.print("[green]✓[/green] Platform API key stored")
    if license_key:
        auth.login_license_key(license_key)
        console.print("[green]✓[/green] Catalog license key stored")
    if master_key:
        auth.login_master_key(master_key)
        console.print("[green]✓[/green] Catalog master key stored")


@app.command()
def logout():
    """Clear all stored credentials."""
    auth.logout()
    console.print("[green]✓[/green] Logged out")


@app.command()
def whoami():
    """Show current authentication state."""
    info = auth.whoami()
    console.print(f"\n  Environment:  [bold]{info['environment']}[/bold]")
    console.print(f"  Gateway:      {info['gateway'] or '[dim]not set[/dim]'}")
    console.print(f"  Catalog:      {info['catalog'] or '[dim]not set[/dim]'}")
    console.print(f"  Auth:         {'[green]authenticated[/green]' if info['authenticated'] else '[yellow]not authenticated[/yellow]'} ({info['method']})")
    console.print(f"  License key:  {'[green]✓[/green]' if info['has_license_key'] else '[dim]—[/dim]'}")
    console.print(f"  Master key:   {'[green]✓[/green]' if info['has_master_key'] else '[dim]—[/dim]'}")
    console.print()


# --- Config commands ---

config_app = typer.Typer(help="Manage CLI configuration.")
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set(key: str = typer.Argument(help="Config key"), value: str = typer.Argument(help="Config value")):
    """Set a configuration value for the current environment."""
    config.set_value(key, value)
    console.print(f"[green]✓[/green] {key} = {value} (env: {config.current_environment()})")


@config_app.command("list")
def config_list():
    """Show current configuration."""
    env = config.current_environment()
    env_config = config.get_env_config()
    console.print(f"\n  [bold]Environment:[/bold] {env}\n")
    for k, v in env_config.items():
        console.print(f"  {k}: {v or '[dim]not set[/dim]'}")
    console.print()


@config_app.command("use")
def config_use(environment: str = typer.Argument(help="Environment name")):
    """Switch to a different environment."""
    config.use_environment(environment)
    console.print(f"[green]✓[/green] Switched to: {environment}")


# --- Version ---

@app.command()
def version():
    """Show CLI version."""
    console.print(f"prox {__version__}")
