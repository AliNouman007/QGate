"""Read-only local Project Intelligence endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from qgate_project_intelligence.models import ProjectKnowledge, ProjectSummary
from qgate_project_intelligence.store import JsonKnowledgeStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/project-intelligence", tags=["project-intelligence"])


class ProjectMapListItem(BaseModel):
    key: str
    source_id: str
    analyzed_at: datetime
    source_fingerprint: str
    summary: ProjectSummary


def _store(request: Request) -> JsonKnowledgeStore:
    settings = request.app.state.settings
    if settings.mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return JsonKnowledgeStore(settings.project_intelligence_dir)


@router.get("/projects", response_model=list[ProjectMapListItem])
async def list_project_maps(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[ProjectMapListItem]:
    store = _store(request)
    return [
        ProjectMapListItem(
            key=store.key_for(project.metadata.source_id),
            source_id=project.metadata.source_id,
            analyzed_at=project.metadata.analyzed_at,
            source_fingerprint=project.metadata.source_fingerprint,
            summary=project.summary,
        )
        for project in store.list_projects()
    ]


@router.get("/latest", response_model=ProjectKnowledge)
async def latest_project_map(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ProjectKnowledge:
    project = _store(request).latest()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no project analyzed yet")
    return project


@router.get("/projects/{key}", response_model=ProjectKnowledge)
async def get_project_map(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ProjectKnowledge:
    project = _store(request).load_key(key)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project map not found")
    return project
