"""Authentication — login, logout, token management."""

import http.server
import json
import threading
import time
import urllib.parse
import webbrowser
from typing import Optional

from . import config
from .api import gateway_get


def login_sso():
    """Open browser for SSO login, capture token via local callback server."""
    # Get auth config from gateway
    gateway = config.get_value("gateway")
    if not gateway:
        raise RuntimeError("Gateway not configured. Run: prox config set gateway <url>")

    try:
        auth_config = gateway_get("/auth/config")
    except Exception as e:
        raise RuntimeError(f"Cannot reach gateway: {e}")

    if not auth_config.get("enabled"):
        raise RuntimeError("SSO not enabled on this gateway (dev mode). Use --api-key instead.")

    authority = auth_config.get("authority", "")
    client_id = auth_config.get("client_id", "")
    scopes = auth_config.get("scopes", "openid profile email")

    if not authority or not client_id:
        raise RuntimeError("Gateway auth config missing authority or client_id")

    # Start local server to receive the callback
    token_result = {"token": None}
    port = 8399
    redirect_uri = f"http://localhost:{port}/callback"

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/callback":
                # Token comes in fragment (implicit) — serve a page that sends it back
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <html><head><meta charset="utf-8"></head><body><script>
                const hash = window.location.hash.substring(1);
                const params = new URLSearchParams(hash);
                const token = params.get('access_token');
                if (token) {
                    fetch('/token?t=' + token).then(() => {
                        document.body.innerHTML = '<h2>Authenticated. You can close this tab.</h2>';
                    });
                } else {
                    document.body.innerHTML = '<h2>No token received.</h2>';
                }
                </script><p>Authenticating...</p></body></html>
                """
                self.wfile.write(html.encode("utf-8"))
            elif parsed.path == "/token":
                qs = urllib.parse.parse_qs(parsed.query)
                token_result["token"] = qs.get("t", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress server logs

    server = http.server.HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)  # Handle callback page
    thread.daemon = True
    thread.start()

    # Also need to handle the /token request
    thread2 = threading.Thread(target=server.handle_request)
    thread2.daemon = True
    thread2.start()

    # Build auth URL (implicit grant)
    auth_url = (
        f"{authority}/oauth2/v2.0/authorize?"
        f"client_id={client_id}"
        f"&response_type=token"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope={urllib.parse.quote(scopes)}"
        f"&response_mode=fragment"
    )

    webbrowser.open(auth_url)

    # Wait for token (timeout 120s)
    deadline = time.time() + 120
    while not token_result["token"] and time.time() < deadline:
        time.sleep(0.5)

    server.server_close()

    if not token_result["token"]:
        raise RuntimeError("Login timed out. No token received within 120 seconds.")

    # Store token
    creds = config.load_credentials()
    creds["token"] = token_result["token"]
    creds["method"] = "sso"
    creds["authenticated_at"] = time.time()
    config.save_credentials(creds)
    return token_result["token"]


def login_api_key(api_key: str):
    """Login with a platform API key."""
    creds = config.load_credentials()
    creds["token"] = api_key
    creds["method"] = "api_key"
    config.save_credentials(creds)


def login_license_key(license_key: str):
    """Store catalog license key."""
    creds = config.load_credentials()
    creds["license_key"] = license_key
    config.save_credentials(creds)


def login_master_key(master_key: str):
    """Store catalog master key (Proxima team only)."""
    creds = config.load_credentials()
    creds["master_key"] = master_key
    config.save_credentials(creds)


def logout():
    """Clear all stored credentials."""
    config.save_credentials({})


def whoami() -> dict:
    """Get current auth state."""
    creds = config.load_credentials()
    return {
        "authenticated": bool(creds.get("token") or creds.get("master_key")),
        "method": creds.get("method", "none"),
        "has_license_key": bool(creds.get("license_key")),
        "has_master_key": bool(creds.get("master_key")),
        "environment": config.current_environment(),
        "gateway": config.get_value("gateway"),
        "catalog": config.get_value("catalog"),
    }
