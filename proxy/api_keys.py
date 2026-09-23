"""Phase 9 (D-058): project-scoped API keys — a credential for CI/SDK/service
integrations that is bound to exactly one project, distinct from a user's
full-account JWT (spec_V3.md §35 "Project Credentials", §57 "Secrets and
Credentials"). sha256, not bcrypt: these are high-entropy random tokens, not
low-entropy user passwords, so a fast hash is the correct/standard choice —
bcrypt's slowness defends against guessing a *short* secret, which doesn't
apply here."""

from __future__ import annotations

import hashlib
import secrets

from pydantic import BaseModel
from sqlalchemy.orm import Session

from proxy.db.models import Project, ProjectAPIKey

_KEY_PREFIX = "sk_live_"


class ApiKeyCreate(BaseModel):
    name: str


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_api_key(db: Session, project_id: int, name: str) -> tuple[ProjectAPIKey, str]:
    """Returns (row, raw_key). The raw key is never stored — only its hash —
    so this is the one and only place the caller can see it."""
    raw_key = _KEY_PREFIX + secrets.token_hex(24)
    row = ProjectAPIKey(project_id=project_id, name=name, key_hash=_hash(raw_key), key_prefix=raw_key[:12])
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, raw_key


def verify_api_key(db: Session, raw_key: str) -> Project | None:
    """Resolves a raw key to its project, or None if unknown/revoked. Also
    stamps last_used_at — best-effort, never blocks the caller's request on
    failure to write it."""
    if not raw_key.startswith(_KEY_PREFIX):
        return None
    row = db.query(ProjectAPIKey).filter(ProjectAPIKey.key_hash == _hash(raw_key)).first()
    if row is None or row.revoked_at is not None:
        return None
    project = db.query(Project).filter(Project.id == row.project_id).first()
    if project is None:
        return None
    from datetime import datetime, timezone

    try:
        row.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
    return project


def revoke_api_key(db: Session, project_id: int, key_id: int) -> bool:
    """Returns False if the key doesn't exist or belongs to a different
    project — the caller turns that into a 404, never confirming existence
    of another project's key."""
    from datetime import datetime, timezone

    row = (
        db.query(ProjectAPIKey)
        .filter(ProjectAPIKey.id == key_id, ProjectAPIKey.project_id == project_id)
        .first()
    )
    if row is None:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def api_key_to_dict(k: ProjectAPIKey) -> dict:
    """Never includes the raw key or its hash."""
    return {
        "id": k.id,
        "project_id": k.project_id,
        "name": k.name,
        "key_prefix": k.key_prefix,
        "created_at": k.created_at,
        "last_used_at": k.last_used_at,
        "revoked_at": k.revoked_at,
        "active": k.revoked_at is None,
    }
