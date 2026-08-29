"""Read-only local Scenario Intelligence endpoints."""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from qgate_scenario_intelligence.models import ScenarioPlan, ScenarioSummary
from qgate_scenario_intelligence.store import JsonScenarioPlanStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/scenario-intelligence", tags=["scenario-intelligence"])


class ScenarioPlanListItem(BaseModel):
    key: str
    generated_at: datetime
    project_source_id: str
    project_fingerprint: str
    impact_change_source_id: str
    summary: ScenarioSummary


def _store(request: Request) -> JsonScenarioPlanStore:
    settings = request.app.state.settings
    if settings.mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    root = os.environ.get(
        "SUITEST_SCENARIO_INTELLIGENCE_DIR", "~/.qgate/scenario-intelligence"
    )
    return JsonScenarioPlanStore(root)


@router.get("/plans", response_model=list[ScenarioPlanListItem])
async def list_scenario_plans(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[ScenarioPlanListItem]:
    store = _store(request)
    return [
        ScenarioPlanListItem(
            key=store.key_for(plan),
            generated_at=plan.metadata.generated_at,
            project_source_id=plan.metadata.project_source_id,
            project_fingerprint=plan.metadata.project_fingerprint,
            impact_change_source_id=plan.metadata.impact_change_source_id,
            summary=plan.summary,
        )
        for plan in store.list_plans()
    ]


@router.get("/latest", response_model=ScenarioPlan)
async def latest_scenario_plan(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ScenarioPlan:
    plan = _store(request).latest()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no scenario plan yet")
    return plan


@router.get("/plans/{key}", response_model=ScenarioPlan)
async def get_scenario_plan(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ScenarioPlan:
    plan = _store(request).load_key(key)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scenario plan not found")
    return plan
