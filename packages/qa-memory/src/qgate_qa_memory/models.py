from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from qgate_project_intelligence.models import Confidence, Evidence

SCHEMA_VERSION = "1.0"
ANALYZER_VERSION = "0.1.0"


class CandidateStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INACTIVE = "inactive"


class MemoryScope(StrEnum):
    PROJECT_SPECIFIC = "project_specific"


class CandidateKind(StrEnum):
    ASSERTION_REGRESSION = "assertion_regression"
    VISUAL_LAYOUT_REGRESSION = "visual_layout_regression"
    STATE_BEHAVIOR_REGRESSION = "state_behavior_regression"
    NAVIGATION_REGRESSION = "navigation_regression"
    CONSOLE_RUNTIME_REGRESSION = "console_runtime_regression"
    NETWORK_BEHAVIOR_REGRESSION = "network_behavior_regression"
    HUMAN_REPORTED = "human_reported"
    OTHER = "other"


class MemorySeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class AuditAction(StrEnum):
    CREATED = "created"
    OCCURRENCE_LINKED = "occurrence_linked"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"


class OccurrenceRef(BaseModel):
    execution_run_id: str | None = None
    scenario_key: str | None = None
    defect_id: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryCandidate(BaseModel):
    key: str
    project_source_id: str
    project_fingerprint: str | None = None
    title: str
    invariant: str
    kind: CandidateKind
    severity: MemorySeverity = MemorySeverity.UNKNOWN
    routes: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    source_scenario_key: str | None = None
    source_execution_run_id: str | None = None
    source_defect_id: str | None = None
    source_impact_keys: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    status: CandidateStatus = CandidateStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_note: str | None = None
    confirmed_memory_key: str | None = None
    dedupe_signature: str
    occurrences: list[OccurrenceRef] = Field(default_factory=list)


class ConfirmedMemory(BaseModel):
    key: str
    project_source_id: str
    title: str
    invariant: str
    scope: MemoryScope = MemoryScope.PROJECT_SPECIFIC
    severity: MemorySeverity = MemorySeverity.UNKNOWN
    routes: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    originating_candidate_keys: list[str] = Field(default_factory=list)
    source_defect_ids: list[str] = Field(default_factory=list)
    source_execution_run_ids: list[str] = Field(default_factory=list)
    source_scenario_keys: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    status: MemoryStatus = MemoryStatus.ACTIVE
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_by: str
    superseded_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    semantic_signature: str


class RegressionRule(BaseModel):
    key: str
    source_memory_key: str
    project_source_id: str
    title: str
    routes: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    expected_invariant: str
    scenario_objective: str
    severity_hint: MemorySeverity = MemorySeverity.UNKNOWN
    active: bool = True
    evidence: list[Evidence] = Field(default_factory=list)


class MemoryAuditEvent(BaseModel):
    key: str
    entity_type: str
    entity_key: str
    action: AuditAction
    actor: str
    note: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecallBudget(BaseModel):
    max_memories: int = Field(default=20, ge=1, le=200)
    max_rules: int = Field(default=20, ge=1, le=200)
    max_evidence_per_item: int = Field(default=5, ge=1, le=20)


class RecalledMemoryMatch(BaseModel):
    memory_key: str
    score: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class RecalledRuleMatch(BaseModel):
    rule_key: str
    source_memory_key: str
    score: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class MemoryRecallGap(BaseModel):
    reason: str
    detail: str | None = None


class MemoryRecallResult(BaseModel):
    project_source_id: str
    project_fingerprint: str
    impact_change_source_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    matched_memories: list[RecalledMemoryMatch] = Field(default_factory=list)
    matched_rules: list[RecalledRuleMatch] = Field(default_factory=list)
    coverage_gaps: list[MemoryRecallGap] = Field(default_factory=list)
    budget: RecallBudget = Field(default_factory=RecallBudget)


class RegressionScenarioHint(BaseModel):
    source_memory_key: str
    source_rule_key: str | None = None
    objective: str
    routes: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    expected_invariant: str
    severity_hint: MemorySeverity = MemorySeverity.UNKNOWN
    evidence: list[Evidence] = Field(default_factory=list)
    requires_runtime_setup: bool = False
    note: str = "Historical regression risk to verify; not evidence that current code is broken."
