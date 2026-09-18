from datetime import datetime

from proxy.db.models import CallLog
from proxy.db.session import get_session


def fetch_calls(since: datetime | None = None) -> list[CallLog]:
    """Never raises — a locked/corrupted DB shows as 'no data' to the dashboard
    instead of crashing the page."""
    db = get_session()
    try:
        query = db.query(CallLog)
        if since:
            query = query.filter(CallLog.created_at >= since)
        return query.order_by(CallLog.created_at.desc()).all()
    except Exception:
        return []
    finally:
        db.close()


def traffic_by_operation(calls: list[CallLog]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in calls:
        counts[c.operation] = counts.get(c.operation, 0) + 1
    return counts


def guardrail_catch_counts(calls: list[CallLog]) -> dict[str, int]:
    injection_catches = 0
    pii_catches = 0
    for c in calls:
        g = c.guardrails or {}
        if g.get("injection", {}).get("flagged"):
            injection_catches += 1
        if g.get("pii", {}).get("found"):
            pii_catches += 1
    return {"injection": injection_catches, "pii": pii_catches}


def hallucination_scores(calls: list[CallLog]) -> list[float]:
    scores = []
    for c in calls:
        h = (c.guardrails or {}).get("hallucination")
        if h:
            scores.append(h["score"])
    return scores


def cost_summary(calls: list[CallLog]) -> dict[str, float]:
    if not calls:
        return {"total_usd": 0.0, "avg_usd": 0.0}
    total = sum(c.cost_estimate_usd for c in calls)
    return {"total_usd": total, "avg_usd": total / len(calls)}


def latency_summary(calls: list[CallLog]) -> dict[str, float]:
    latencies = sorted(c.latency_ms for c in calls)
    if not latencies:
        return {"avg_ms": 0.0, "p95_ms": 0.0}
    avg = sum(latencies) / len(latencies)
    p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
    return {"avg_ms": avg, "p95_ms": p95}
