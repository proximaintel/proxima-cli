"""Configuration management — ~/.prox/ directory."""

import json
from pathlib import Path
from typing import Optional

PROX_DIR = Path.home() / ".prox"
CONFIG_FILE = PROX_DIR / "config.json"
CREDENTIALS_FILE = PROX_DIR / "credentials.json"
PACKAGES_DIR = PROX_DIR / "packages"

DEFAULT_CONFIG = {
    "environment": "local",
    "environments": {
        "local": {
            "gateway": "http://localhost:9000",
            "catalog": "https://catalog.proximaintel.com",
            "registry": "",
        }
    },
}


def ensure_dirs():
    PROX_DIR.mkdir(exist_ok=True)
    PACKAGES_DIR.mkdir(exist_ok=True)


def load_config() -> dict:
    ensure_dirs()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict):
    ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_env_config() -> dict:
    """Get the active environment's config."""
    config = load_config()
    env = config.get("environment", "local")
    return config.get("environments", {}).get(env, {})


def get_value(key: str) -> Optional[str]:
    return get_env_config().get(key)


def set_value(key: str, value: str):
    config = load_config()
    env = config.get("environment", "local")
    if env not in config.get("environments", {}):
        config.setdefault("environments", {})[env] = {}
    config["environments"][env][key] = value
    save_config(config)


def use_environment(name: str):
    config = load_config()
    if name not in config.get("environments", {}):
        config.setdefault("environments", {})[name] = {}
    config["environment"] = name
    save_config(config)


def current_environment() -> str:
    return load_config().get("environment", "local")


# --- Credentials ---

def load_credentials() -> dict:
    ensure_dirs()
    if not CREDENTIALS_FILE.exists():
        return {}
    return json.loads(CREDENTIALS_FILE.read_text())


def save_credentials(creds: dict):
    ensure_dirs()
    CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def get_token() -> Optional[str]:
    return load_credentials().get("token")


def get_license_key() -> Optional[str]:
    return load_credentials().get("license_key")


def get_master_key() -> Optional[str]:
    return load_credentials().get("master_key")
