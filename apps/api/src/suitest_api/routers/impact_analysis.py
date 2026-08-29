"""Read-only local Impact Analysis endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from qgate_impact_analysis.models import ImpactReport, ImpactSummary
from qgate_impact_analysis.store import JsonImpactStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/impact-analysis", tags=["impact-analysis"])


class ImpactReportListItem(BaseModel):
    key: str
    analyzed_at: datetime
    project_source_id: str
    project_fingerprint: str
    change_source_id: str
    summary: ImpactSummary


def _store(request: Request) -> JsonImpactStore:
    settings = request.app.state.settings
    if settings.mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return JsonImpactStore(settings.impact_analysis_dir)


@router.get("/reports", response_model=list[ImpactReportListItem])
async def list_impact_reports(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[ImpactReportListItem]:
    store = _store(request)
    reports = store.list_reports()
    return [
        ImpactReportListItem(
            key=store.key_for(report),
            analyzed_at=report.metadata.analyzed_at,
            project_source_id=report.metadata.project_source_id,
            project_fingerprint=report.metadata.project_fingerprint,
            change_source_id=report.metadata.change_source_id,
            summary=report.summary,
        )
        for report in reports
    ]


@router.get("/latest", response_model=ImpactReport)
async def latest_impact_report(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ImpactReport:
    report = _store(request).latest()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no impact report yet")
    return report


@router.get("/reports/{key}", response_model=ImpactReport)
async def get_impact_report(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ImpactReport:
    report = _store(request).load_key(key)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="impact report not found")
    return report
