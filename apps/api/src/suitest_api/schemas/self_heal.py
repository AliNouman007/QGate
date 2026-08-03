"""API contracts for selector self-healing."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SelectorRepairRequest(BaseModel):
    step_id: str
    error: str = Field(min_length=1, max_length=20_000)
    dom_snapshot: str | None = Field(default=None, max_length=100_000)


class SelectorRepairPublic(BaseModel):
    step_id: str
    failure_kind: str = "selector_changed"
    old_selector: str
    new_selector: str
    updated_code: str
    rationale: str
    confidence: float
    code_sha256: str


class SelectorRepairApplyRequest(BaseModel):
    step_id: str
    old_selector: str = Field(min_length=1, max_length=500)
    new_selector: str = Field(min_length=1, max_length=500)
    code_sha256: str = Field(min_length=64, max_length=64)
    rationale: str | None = Field(default=None, max_length=1000)


class SelectorRepairApplied(BaseModel):
    step_id: str
    code: str
    old_selector: str
    new_selector: str
    applied: bool = True


__all__ = [
    "SelectorRepairApplied",
    "SelectorRepairApplyRequest",
    "SelectorRepairPublic",
    "SelectorRepairRequest",
]
