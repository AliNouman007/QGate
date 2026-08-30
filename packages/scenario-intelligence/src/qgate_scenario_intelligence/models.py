from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from qgate_project_intelligence.models import Confidence, Evidence

SCHEMA_VERSION = "1.1"
ANALYZER_VERSION = "0.2.0"


class ScenarioKind(StrEnum):
    SMOKE = "smoke"
    STATE_VARIANT = "state_variant"
    NEGATIVE_STATE = "negative_state"
    CROSS_STATE_COMPARISON = "cross_state_comparison"
    ROUTE_REGRESSION = "route_regression"
    RUNTIME_DISCOVERY = "runtime_discovery"


class ScenarioPriority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class AutomationReadiness(StrEnum):
    READY = "ready"
    RUNTIME_DISCOVERY_REQUIRED = "runtime_discovery_required"
    MANUAL_ONLY = "manual_only"
    BLOCKED_BY_GAP = "blocked_by_gap"


class StateSetupMechanism(StrEnum):
    UI_CONTROL = "ui_control"


class StateSetupHint(BaseModel):
    state_key: str
    state_label: str
    mechanism: StateSetupMechanism
    target_label: str
    value: str | None = None
    verification_text: str | None = None
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)


class GenerationBudget(BaseModel):
    max_scenarios: int = Field(default=40, ge=1, le=500)
    max_state_variants_per_surface: int = Field(default=6, ge=1, le=50)
    max_cross_state_groups: int = Field(default=10, ge=0, le=100)


class ScenarioStep(BaseModel):
    action: str
    expected: str
    target_kind: str = "FE_WEB"
    route: str | None = None
    data_hint: str | None = None


class Scenario(BaseModel):
    key: str
    title: str
    kind: ScenarioKind
    priority: ScenarioPriority
    confidence: Confidence
    routes: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    state_setup_hints: list[StateSetupHint] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[ScenarioStep] = Field(default_factory=list)
    reason: str
    source_impact_keys: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    readiness: AutomationReadiness
    needs_runtime_discovery: bool = False
    manual_reason: str | None = None
    cross_state_group: str | None = None
    explanation: str | None = None
    priority_hint: str | None = None


class CrossStateGroup(BaseModel):
    key: str
    route: str | None = None
    state_labels: list[str] = Field(default_factory=list)
    scenario_keys: list[str] = Field(default_factory=list)
    comparison_goal: str


class ScenarioCoverageGap(BaseModel):
    reason: str
    detail: str | None = None
    source_impact_key: str | None = None


class ScenarioSummary(BaseModel):
    total: int = 0
    ready: int = 0
    runtime_discovery: int = 0
    manual_only: int = 0
    blocked: int = 0
    p0: int = 0
    p1: int = 0
    p2: int = 0
    p3: int = 0


class ScenarioPlanMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    analyzer_version: str = ANALYZER_VERSION
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_source_id: str
    project_fingerprint: str
    impact_change_source_id: str


class ScenarioPlan(BaseModel):
    metadata: ScenarioPlanMetadata
    budget: GenerationBudget
    summary: ScenarioSummary
    scenarios: list[Scenario] = Field(default_factory=list)
    cross_state_groups: list[CrossStateGroup] = Field(default_factory=list)
    coverage_gaps: list[ScenarioCoverageGap] = Field(default_factory=list)
