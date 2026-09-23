"""Phase 11 (D-050): continuous security monitoring — event model, recording,
filtering, retention. Events are observations, not vulnerabilities: nothing
here creates or changes a Finding.

Recording never breaks the request that triggered it: a failed write is
logged (explicitly, not swallowed silently) and rolled back, and the caller's
response is unaffected."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from proxy.config import settings
from proxy.db.models import SecurityEvent
from proxy.db.session import get_session

log = logging.getLogger("sentinelai.events")

ATTACK_ATTEMPT = "attack_attempt"
REQUEST_BLOCKED = "request_blocked"
POLICY_VIOLATION = "policy_violation"
FINDING_OPENED = "finding_opened"
REGRESSION_DETECTED = "regression_detected"
SUSPICIOUS_TOOL_ACTIVITY = "suspicious_tool_activity"
EVENT_TYPES = [
    ATTACK_ATTEMPT,
    REQUEST_BLOCKED,
    POLICY_VIOLATION,
    FINDING_OPENED,
    REGRESSION_DETECTED,
    SUSPICIOUS_TOOL_ACTIVITY,
]

SEVERITIES = ["info", "low", "medium", "high", "critical"]
_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def record_event(
    db: Session,
    *,
    event_type: str,
    severity: str,
    category: str,
    source: str,
    summary: str,
    application: str | None = None,
    model: str | None = None,
    details: dict | None = None,
    project_id: int | None = None,
) -> SecurityEvent | None:
    """`summary`/`details` must be metadata (pattern names, types, ids) —
    callers never pass prompt or response text. `project_id` is None for
    events from execution sources outside the project model (e.g. the
    gateway) — those remain visible only via source="gateway" filtering,
    never through a project-scoped /v1/events call (D-055)."""
    if not settings.events_enabled:
        return None
    if _RANK.get(severity, 0) < _RANK[settings.events_min_severity]:
        return None
    try:
        event = SecurityEvent(
            project_id=project_id,
            event_type=event_type,
            severity=severity,
            category=category,
            source=source,
            summary=summary,
            application=application,
            model=model,
            details=details or {},
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception:
        log.exception("Failed to record security event %s", event_type)
        db.rollback()
        return None


def record_event_standalone(**fields) -> None:
    """For callers without a DB session (the gateway's optional sink)."""
    db = get_session()
    try:
        record_event(db, **fields)
    finally:
        db.close()


def _csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def query_events(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    severity: str | None = None,
    min_severity: str | None = None,
    application: str | None = None,
    model: str | None = None,
    category: str | None = None,
    event_type: str | None = None,
    limit: int = 200,
    project_id: int | None = None,
) -> list[SecurityEvent]:
    q = db.query(SecurityEvent)
    if project_id is not None:
        q = q.filter(SecurityEvent.project_id == project_id)
    if since:
        q = q.filter(SecurityEvent.created_at >= since)
    if until:
        q = q.filter(SecurityEvent.created_at <= until)
    if sev := _csv(severity):
        q = q.filter(SecurityEvent.severity.in_(sev))
    if min_severity in _RANK:
        q = q.filter(SecurityEvent.severity.in_(SEVERITIES[_RANK[min_severity]:]))
    if application:
        q = q.filter(SecurityEvent.application == application)
    if model:
        q = q.filter(SecurityEvent.model == model)
    if cats := _csv(category):
        q = q.filter(SecurityEvent.category.in_(cats))
    if types := _csv(event_type):
        q = q.filter(SecurityEvent.event_type.in_(types))
    return q.order_by(SecurityEvent.created_at.desc()).limit(limit).all()


def purge_expired(db: Session, retention_days: int | None = None) -> int:
    days = settings.events_retention_days if retention_days is None else retention_days
    if days <= 0:  # 0 or negative = keep forever
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = db.query(SecurityEvent).filter(SecurityEvent.created_at < cutoff).delete()
    db.commit()
    return deleted


def event_to_dict(e: SecurityEvent) -> dict:
    return {
        "id": e.id,
        "project_id": e.project_id,
        "event_type": e.event_type,
        "severity": e.severity,
        "category": e.category,
        "source": e.source,
        "application": e.application,
        "model": e.model,
        "summary": e.summary,
        "details": e.details,
        "created_at": e.created_at,
    }


def events_config() -> dict:
    return {
        "enabled": settings.events_enabled,
        "retention_days": settings.events_retention_days,
        "min_severity": settings.events_min_severity,
        "gateway_record_events": settings.gateway_record_events,
        "event_types": EVENT_TYPES,
        "severities": SEVERITIES,
    }
