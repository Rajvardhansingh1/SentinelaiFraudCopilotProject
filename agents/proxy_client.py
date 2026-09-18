import os

import requests

PROXY_BASE_URL = os.environ.get("PROXY_BASE_URL", "http://localhost:8000")


class ProxyCallFailed(Exception):
    """Raised on connection errors only. Non-200 HTTP responses are returned, not raised —
    callers (LangGraph nodes) decide how to record guardrail rejections (D-024)."""


def call_proxy(
    session_id: str,
    operation: str,
    messages: list[dict],
    schema_name: str | None = None,
    grounding_context: str | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict]:
    """POST /v1/generate. Returns (status_code, body). Agents never call an LLM provider
    directly (D-002) — this is the only path to the LLM."""
    try:
        resp = requests.post(
            f"{PROXY_BASE_URL}/v1/generate",
            json={
                "session_id": session_id,
                "operation": operation,
                "messages": messages,
                "schema_name": schema_name,
                "grounding_context": grounding_context,
            },
            timeout=timeout,
        )
        return resp.status_code, resp.json()
    except requests.RequestException as exc:
        # Covers connection errors AND non-JSON bodies (requests.exceptions.JSONDecodeError
        # is itself a RequestException) — a non-JSON body means an unhandled exception
        # escaped the proxy endpoint (plain-text 500). Don't crash the caller either way.
        raise ProxyCallFailed(str(exc)) from exc
