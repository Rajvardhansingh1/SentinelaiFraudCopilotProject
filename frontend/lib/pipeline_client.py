from agents.graph import build_graph

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_on_receipt(session_id: str, image_path: str) -> dict:
    """Runs the compiled LangGraph pipeline in-process (no HTTP hop — LangGraph is a
    library, not a service; the proxy is the only HTTP boundary, per PHASE6_PLAN.md §3).
    Never raises — any node failure not already caught inside agents/graph.py's own
    per-node guards is surfaced as an explicit error entry, not a crashed page."""
    graph = _get_graph()
    try:
        return graph.invoke({"session_id": session_id, "image_path": image_path, "errors": []})
    except Exception as exc:
        return {
            "session_id": session_id,
            "image_path": image_path,
            "extracted_fields": None,
            "forensics_result": None,
            "policy_verdict": None,
            "report_text": None,
            "report_guardrails": None,
            "errors": [{"node": "pipeline", "code": "pipeline_failed", "message": str(exc)}],
        }
