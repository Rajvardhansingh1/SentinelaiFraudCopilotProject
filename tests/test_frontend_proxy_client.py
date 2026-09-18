from unittest.mock import Mock, patch

import requests

from frontend.lib.proxy_client import call_generate


def test_call_generate_returns_error_envelope_on_connection_failure():
    with patch("frontend.lib.proxy_client.requests.post", side_effect=requests.ConnectionError("refused")):
        status, body = call_generate("s1", "hello")
    assert status == 503
    assert body["error"]["code"] == "proxy_unreachable"
    assert body["guardrails"]["injection"]["flagged"] is False


def test_call_generate_returns_error_envelope_on_non_json_response():
    """Regression: a plain-text 500 used to crash the Streamlit page with an uncaught
    requests.exceptions.JSONDecodeError."""
    fake_resp = Mock()
    fake_resp.status_code = 500
    fake_resp.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    with patch("frontend.lib.proxy_client.requests.post", return_value=fake_resp):
        status, body = call_generate("s1", "hello")
    assert status == 503
    assert body["error"]["code"] == "proxy_unreachable"
