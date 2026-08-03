"""Risk-based test strategy API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from suitest_shared.domain.enums import (
    TestingApproach,
    TestLevel,
    TestStrategyStatus,
)


class StrategyRisk(BaseModel):
    id: str
    title: str
    impact: str
    likelihood: str
    failure_modes: list[str] = Field(default_factory=list)
    recommended_approach: TestingApproach
    test_levels: list[TestLevel] = Field(default_factory=list)


class TestStrategyDocument(BaseModel):
    schema_version: str = "1"
    summary: str
    recommended_approach: TestingApproach
    approach_reason: str
    access_signals: list[str] = Field(default_factory=list)
    risks: list[StrategyRisk] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    oracles: list[str] = Field(default_factory=list)
    coverage_dimensions: list[str] = Field(default_factory=list)
    qa_checks: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    enrichment: str = "DETERMINISTIC"


class TestStrategyDraftRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    has_repository: bool = Field(default=False, alias="hasRepository")
    has_internal_observability: bool = Field(default=False, alias="hasInternalObservability")
    has_internal_test_provider: bool = Field(default=False, alias="hasInternalTestProvider")
    context: str = Field(default="", max_length=4000)


class TestStrategyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: TestStrategyDocument


class TestStrategyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    project_id: str
    version: int
    status: TestStrategyStatus
    document: TestStrategyDocument
    agent_session_id: str | None = None
    created_by: uuid.UUID | None = None
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
