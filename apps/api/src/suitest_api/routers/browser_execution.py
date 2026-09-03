"""Read-only local QGate Browser Execution & Evidence endpoints."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qgate_browser_execution.models import ExecutionReport, ExecutionSummary
from qgate_browser_execution.store import JsonExecutionReportStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/browser-execution", tags=["browser-execution"])


class ExecutionReportListItem(BaseModel):
    key: str
    run_id: str
    started_at: datetime
    scenario_plan_key: str
    project_source_id: str
    project_fingerprint: str
    summary: ExecutionSummary


def _store(request: Request) -> JsonExecutionReportStore:
    settings = request.app.state.settings
    mode = os.environ.get("SUITEST_MODE", settings.mode)
    if mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    root = os.environ.get("SUITEST_BROWSER_EXECUTION_DIR", "~/.qgate/browser-execution")
    return JsonExecutionReportStore(root)


@router.get("/reports", response_model=list[ExecutionReportListItem])
async def list_execution_reports(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[ExecutionReportListItem]:
    store = _store(request)
    return [
        ExecutionReportListItem(
            key=store.key_for(report),
            run_id=report.metadata.run_id,
            started_at=report.metadata.started_at,
            scenario_plan_key=report.metadata.scenario_plan_key,
            project_source_id=report.metadata.project_source_id,
            project_fingerprint=report.metadata.project_fingerprint,
            summary=report.summary,
        )
        for report in store.list_reports()
    ]


@router.get("/latest", response_model=ExecutionReport)
async def latest_execution_report(
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ExecutionReport:
    report = _store(request).latest()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no execution report yet")
    return report


@router.get("/reports/{key}", response_model=ExecutionReport)
async def get_execution_report(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ExecutionReport:
    report = _store(request).load_key(key)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution report not found")
    return report


@router.get("/artifacts/{subpath:path}")
async def get_execution_artifact(subpath: str, request: Request) -> FileResponse:
    """Serve visual evidence (screenshots, videos) captured during browser execution."""
    root = (
        Path(
            os.path.expanduser(
                os.environ.get(
                    "SUITEST_BROWSER_EXECUTION_DIR", "~/.qgate/browser-execution"
                )
            )
        )
        / "artifacts"
    ).resolve()
    target = (root / subpath).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")

    ext = target.suffix.lower()
    media_type = (
        "image/png"
        if ext == ".png"
        else "video/webm"
        if ext == ".webm"
        else "application/octet-stream"
    )
    return FileResponse(target, media_type=media_type)

