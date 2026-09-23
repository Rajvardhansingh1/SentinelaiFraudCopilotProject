"""Phase 2 (D-055): workspace/project model and isolation.

Every user gets exactly one workspace, auto-created on signup (see
proxy/main.py's signup handler) — spec_V3.md's User→Workspace→Project
hierarchy without building cross-user workspace membership, which nothing
in Phase 2 asks for."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from proxy.auth import get_current_user
from proxy.db.models import Project, User, Workspace
from proxy.db.session import get_session

TARGET_TYPES = ("model", "application", "agent", "api", "service")


class ProjectCreate(BaseModel):
    name: str
    target_type: str = "model"


def create_workspace_for_user(db, user_id: int, name: str = "My Workspace") -> Workspace:
    workspace = Workspace(owner_user_id=user_id, name=name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def project_to_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "workspace_id": p.workspace_id,
        "name": p.name,
        "target_type": p.target_type,
        "created_at": p.created_at,
    }


def owned_project(db, project_id: int, user: User) -> Project:
    """The single choke point every project-scoped code path routes
    through — spec_V3.md §9's "a request for Project A must never return
    Project B data" lives here, not re-implemented per call site. 404, not
    403, on mismatch — never confirm a project ID exists to someone who
    doesn't own it (avoids leaking project existence via enumeration)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found", "message": "No such project."})
    workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()
    if workspace is None or workspace.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "project_not_found", "message": "No such project."})
    return project


def require_project(project_id: int, user: User = Depends(get_current_user)) -> Project:
    """FastAPI dependency form of owned_project() — for endpoints where
    project_id is a query/path parameter (most of them). Endpoints where
    project_id arrives inside a JSON body (e.g. POST /v1/generate) call
    owned_project() directly instead."""
    db = get_session()
    try:
        project = owned_project(db, project_id, user)
        db.expunge(project)
        return project
    finally:
        db.close()
