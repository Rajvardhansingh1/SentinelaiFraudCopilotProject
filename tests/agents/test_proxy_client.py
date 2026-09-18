from unittest.mock import Mock, patch

import pytest
import requests

from agents.proxy_client import ProxyCallFailed, call_proxy


def test_call_proxy_raises_on_connection_error():
    with patch("agents.proxy_client.requests.post", side_effect=requests.ConnectionError("refused")):
        with pytest.raises(ProxyCallFailed):
            call_proxy("s1", "extract", [{"role": "user", "content": "x"}])


def test_call_proxy_raises_not_crashes_on_non_json_response():
    """Regression: a plain-text 500 (unhandled exception escaping the proxy) used to
    raise an uncaught requests.exceptions.JSONDecodeError instead of ProxyCallFailed."""
    fake_resp = Mock()
    fake_resp.status_code = 500
    fake_resp.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    with patch("agents.proxy_client.requests.post", return_value=fake_resp):
        with pytest.raises(ProxyCallFailed):
            call_proxy("s1", "extract", [{"role": "user", "content": "x"}])
