# Proxima CLI

The official command-line interface for **Proxima AIP** — manage your AI agent platform from the terminal.

## Install

```bash
pipx install proxima-cli
# or
pip install proxima-cli
```

## Quick Start

```bash
# Login (opens browser for SSO)
prox login

# Check connection
prox whoami

# List agents
prox agent list

# Create a domain
prox domain create --id finance --name "Finance"

# Deploy an agent from a package
prox agent deploy --from ./my-agent/
```

## Configuration

```bash
# Set your platform gateway URL
prox config set gateway https://gateway.your-platform.com

# Set catalog (for pulling pre-built agents)
prox config set catalog https://catalog.proximaintel.com

# View config
prox config list
```

## Commands

| Command Group | Description |
|---|---|
| `prox login / logout / whoami` | Authentication |
| `prox config` | Environment configuration |
| `prox catalog` | Browse and pull agents from Proxima Catalog |
| `prox agent` | Create, configure, deploy, publish agents |
| `prox toolbox` | Build and register toolboxes |
| `prox knowledge` | Manage data sources and knowledge bases |
| `prox secret` | Manage credentials |
| `prox model` | Register LLM providers |
| `prox ontology` | Manage entity models |
| `prox routine` | Schedule autonomous agent execution |
| `prox workflow` | Multi-agent orchestration pipelines |
| `prox governance` | Audit logs and usage stats |
| `prox platform` | Health checks and service management |

## Agent Deployment

```bash
prox agent deploy --from ./my-agent/
```

Expects:
```
my-agent/
├── agent.yaml           # Agent config
├── toolbox/             # Optional: custom tools
│   ├── tools.py
│   ├── Dockerfile
│   └── requirements.txt
├── knowledge.yaml       # Data source requirements
└── workspace.json       # Dashboard layout
```

One command. Full agent. Production-ready.

## CI/CD

```bash
prox login --api-key $PLATFORM_API_KEY
prox config set gateway $GATEWAY_URL
prox agent deploy --from ./agents/my-agent/
```

## Documentation

Full docs at [docs.proximaintel.com/cli](https://docs.proximaintel.com/cli)
