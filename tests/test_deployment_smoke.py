import os

import pytest
import requests

DEPLOYED_PROXY_URL = os.environ.get("DEPLOYED_PROXY_URL")


@pytest.mark.skipif(not DEPLOYED_PROXY_URL, reason="DEPLOYED_PROXY_URL not set — no live deployment to check")
def test_deployed_proxy_health_check():
    resp = requests.get(f"{DEPLOYED_PROXY_URL}/health", timeout=35)
    assert resp.status_code == 200


@pytest.mark.skipif(not DEPLOYED_PROXY_URL, reason="DEPLOYED_PROXY_URL not set — no live deployment to check")
def test_deployed_proxy_quota_endpoint():
    resp = requests.get(f"{DEPLOYED_PROXY_URL}/quota", timeout=35)
    assert resp.status_code == 200
    assert "calls_today" in resp.json()
