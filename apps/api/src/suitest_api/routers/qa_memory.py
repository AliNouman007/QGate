"""Local authenticated QGate QA Memory endpoints."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from qgate_qa_memory.lifecycle import InvalidMemoryTransitionError, QAMemoryService
from qgate_qa_memory.models import ConfirmedMemory, MemoryCandidate, RegressionRule
from qgate_qa_memory.store import JsonQAMemoryStore

from suitest_api.deps.scope import TenantContext, require_workspace_membership

router = APIRouter(prefix="/qa-memory", tags=["qa-memory"])


class ReviewPayload(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    create_rule: bool = True


class SupersedePayload(BaseModel):
    replacement_key: str
    note: str | None = Field(default=None, max_length=2000)


class LifecyclePayload(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class CandidateReviewResult(BaseModel):
    candidate: MemoryCandidate
    memory: ConfirmedMemory | None = None
    rule: RegressionRule | None = None


def _store(request: Request) -> JsonQAMemoryStore:
    settings = request.app.state.settings
    mode = os.environ.get("SUITEST_MODE", settings.mode)
    if mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    root = os.environ.get("SUITEST_QA_MEMORY_DIR", "~/.qgate/qa-memory")
    return JsonQAMemoryStore(root)


def _translate_transition_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/candidates", response_model=list[MemoryCandidate])
async def list_candidates(
    request: Request,
    project_source_id: str | None = None,
    status_filter: Literal["pending", "confirmed", "rejected"] | None = None,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[MemoryCandidate]:
    items = _store(request).list_candidates(project_source_id=project_source_id)
    if status_filter is not None:
        items = [item for item in items if item.status.value == status_filter]
    return items


@router.get("/candidates/{key}", response_model=MemoryCandidate)
async def get_candidate(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> MemoryCandidate:
    item = _store(request).load_candidate(key)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
    return item


@router.get("/memories", response_model=list[ConfirmedMemory])
async def list_memories(
    request: Request,
    project_source_id: str | None = None,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[ConfirmedMemory]:
    return _store(request).list_memories(project_source_id=project_source_id)


@router.get("/memories/{key}", response_model=ConfirmedMemory)
async def get_memory(
    key: str,
    request: Request,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> ConfirmedMemory:
    item = _store(request).load_memory(key)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory not found")
    return item


@router.get("/rules", response_model=list[RegressionRule])
async def list_rules(
    request: Request,
    project_source_id: str | None = None,
    _ctx: TenantContext = Depends(require_workspace_membership),
) -> list[RegressionRule]:
    return _store(request).list_rules(project_source_id=project_source_id)


@router.post("/candidates/{key}/confirm", response_model=CandidateReviewResult)
async def confirm_candidate(
    key: str,
    payload: ReviewPayload,
    request: Request,
    ctx: TenantContext = Depends(require_workspace_membership),
) -> CandidateReviewResult:
    service = QAMemoryService(_store(request))
    try:
        candidate, memory, rule = service.confirm_candidate(
            key,
            reviewer=ctx.user_id,
            note=payload.note,
            create_rule=payload.create_rule,
        )
    except (KeyError, InvalidMemoryTransitionError) as exc:
        raise _translate_transition_error(exc) from exc
    return CandidateReviewResult(candidate=candidate, memory=memory, rule=rule)


@router.post("/candidates/{key}/reject", response_model=CandidateReviewResult)
async def reject_candidate(
    key: str,
    payload: LifecyclePayload,
    request: Request,
    ctx: TenantContext = Depends(require_workspace_membership),
) -> CandidateReviewResult:
    service = QAMemoryService(_store(request))
    try:
        candidate = service.reject_candidate(key, reviewer=ctx.user_id, note=payload.note)
    except (KeyError, InvalidMemoryTransitionError) as exc:
        raise _translate_transition_error(exc) from exc
    return CandidateReviewResult(candidate=candidate)


@router.post("/memories/{key}/supersede", response_model=ConfirmedMemory)
async def supersede_memory(
    key: str,
    payload: SupersedePayload,
    request: Request,
    ctx: TenantContext = Depends(require_workspace_membership),
) -> ConfirmedMemory:
    try:
        return QAMemoryService(_store(request)).supersede_memory(
            key,
            replacement_key=payload.replacement_key,
            reviewer=ctx.user_id,
            note=payload.note,
        )
    except (KeyError, InvalidMemoryTransitionError) as exc:
        raise _translate_transition_error(exc) from exc


@router.post("/memories/{key}/deactivate", response_model=ConfirmedMemory)
async def deactivate_memory(
    key: str,
    payload: LifecyclePayload,
    request: Request,
    ctx: TenantContext = Depends(require_workspace_membership),
) -> ConfirmedMemory:
    try:
        return QAMemoryService(_store(request)).deactivate_memory(
            key, reviewer=ctx.user_id, note=payload.note
        )
    except (KeyError, InvalidMemoryTransitionError) as exc:
        raise _translate_transition_error(exc) from exc


@router.post("/memories/{key}/reactivate", response_model=ConfirmedMemory)
async def reactivate_memory(
    key: str,
    payload: LifecyclePayload,
    request: Request,
    ctx: TenantContext = Depends(require_workspace_membership),
) -> ConfirmedMemory:
    try:
        return QAMemoryService(_store(request)).reactivate_memory(
            key, reviewer=ctx.user_id, note=payload.note
        )
    except (KeyError, InvalidMemoryTransitionError) as exc:
        raise _translate_transition_error(exc) from exc
