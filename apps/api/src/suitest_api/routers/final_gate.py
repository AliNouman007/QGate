"""Read-only local QGate Final Gate report endpoints."""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from qgate_final_gate.models import GateReport, GateVerdict
from qgate_final_gate.store import JsonGateReportStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/final-gate", tags=["final-gate"])


class GateReportListItem(BaseModel):
    key: str
    generated_at: datetime
    verdict: GateVerdict
    headline: str
    project_source_id: str
    project_fingerprint: str
    change_source_id: str
    execution_run_id: str


def _store(request: Request) -> JsonGateReportStore:
    settings = request.app.state.settings
    mode = os.environ.get("SUITEST_MODE", settings.mode)
    if mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    root = os.environ.get("SUITEST_FINAL_GATE_DIR", "~/.qgate/final-gate")
    return JsonGateReportStore(root)


@router.get("/reports", response_model=list[GateReportListItem])
async def list_gate_reports(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[GateReportListItem]:
    return [
        GateReportListItem(
            key=report.metadata.report_key,
            generated_at=report.metadata.generated_at,
            verdict=report.verdict,
            headline=report.headline,
            project_source_id=report.metadata.project_source_id,
            project_fingerprint=report.metadata.project_fingerprint,
            change_source_id=report.metadata.change_source_id,
            execution_run_id=report.metadata.execution_run_id,
        )
        for report in _store(request).list_reports()
    ]


@router.get("/latest", response_model=GateReport)
async def latest_gate_report(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> GateReport:
    report = _store(request).latest()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no final gate report yet")
    return report


@router.get("/reports/{key}", response_model=GateReport)
async def get_gate_report(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> GateReport:
    report = _store(request).load_key(key)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="final gate report not found")
    return report
