import requests

from frontend.lib.proxy_client import PROXY_BASE_URL


def ping_proxy(timeout: float = 1.0) -> bool:
    """GET /health with a short timeout. False = likely cold/sleeping or unreachable."""
    try:
        resp = requests.get(f"{PROXY_BASE_URL}/health", timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False
