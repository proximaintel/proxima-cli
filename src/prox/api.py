"""HTTP client for gateway and catalog APIs."""

import httpx
from typing import Optional
from . import config


class APIError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"[{status}] {detail}")


def _gateway_url() -> str:
    url = config.get_value("gateway")
    if not url:
        raise APIError(0, "Gateway URL not configured. Run: prox config set gateway <url>")
    return url.rstrip("/")


def _catalog_url() -> str:
    url = config.get_value("catalog") or "https://catalog.proximaintel.com"
    return url.rstrip("/")


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = config.get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _catalog_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    master = config.get_master_key()
    if master:
        headers["X-Master-Key"] = master
    else:
        lic = config.get_license_key()
        if lic:
            headers["X-License-Key"] = lic
    return headers


# --- Gateway calls ---

def gateway_get(path: str, params: Optional[dict] = None) -> dict:
    url = f"{_gateway_url()}{path}"
    r = httpx.get(url, headers=_headers(), params=params, timeout=30, verify=False)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


def gateway_post(path: str, data: Optional[dict] = None) -> dict:
    url = f"{_gateway_url()}{path}"
    r = httpx.post(url, headers=_headers(), json=data, timeout=60, verify=False)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


def gateway_put(path: str, data: Optional[dict] = None) -> dict:
    url = f"{_gateway_url()}{path}"
    r = httpx.put(url, headers=_headers(), json=data, timeout=60, verify=False)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


def gateway_delete(path: str) -> dict:
    url = f"{_gateway_url()}{path}"
    r = httpx.delete(url, headers=_headers(), timeout=30, verify=False)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


# --- Catalog calls ---

def catalog_get(path: str, params: Optional[dict] = None) -> dict:
    url = f"{_catalog_url()}{path}"
    r = httpx.get(url, headers=_catalog_headers(), params=params, timeout=30)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


def catalog_post(path: str, data: Optional[dict] = None) -> dict:
    url = f"{_catalog_url()}{path}"
    r = httpx.post(url, headers=_catalog_headers(), json=data, timeout=60)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:500])
    return r.json()


def catalog_download(path: str, dest: str):
    """Download a file from the catalog to a local path."""
    url = f"{_catalog_url()}{path}"
    with httpx.stream("GET", url, headers=_catalog_headers(), timeout=120) as r:
        if r.status_code >= 400:
            raise APIError(r.status_code, f"Download failed: {r.status_code}")
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
