from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from qgate_browser_execution.models import FailureCategory
from qgate_impact_analysis.models import ImpactReport
from qgate_project_intelligence.models import Evidence, ProjectKnowledge
from qgate_qa_memory.models import MemoryRecallResult
from qgate_scenario_intelligence.models import AutomationReadiness, ScenarioPlan, ScenarioPriority

SCHEMA_VERSION = "1.0"
GATE_VERSION = "0.1.0"


class GateVerdict(StrEnum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class GateConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerdictEffect(StrEnum):
    BLOCKING = "blocking"
    MANUAL_REVIEW = "manual_review"
    INFORMATIONAL = "informational"


class GateReasonKind(StrEnum):
    VERIFIED_PRODUCT_FAILURE = "verified_product_failure"
    REQUIRED_SCENARIO_UNVERIFIED = "required_scenario_unverified"
    REQUIRED_SCENARIO_BLOCKED = "required_scenario_blocked"
    REQUIRED_SCENARIO_MANUAL_ONLY = "required_scenario_manual_only"
    ENVIRONMENT_OR_SETUP_GAP = "environment_or_setup_gap"
    TARGET_RESOLUTION_GAP = "target_resolution_gap"
    TEST_DEFINITION_GAP = "test_definition_gap"
    TIMEOUT_UNRESOLVED = "timeout_unresolved"
    HISTORICAL_REGRESSION_UNVERIFIED = "historical_regression_unverified"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    INPUT_INTEGRITY_GAP = "input_integrity_gap"
    COVERAGE_TRUNCATED = "coverage_truncated"
    NO_REQUIRED_COVERAGE = "no_required_coverage"
    ALL_REQUIRED_COVERAGE_VERIFIED = "all_required_coverage_verified"


class CoverageOutcome(StrEnum):
    VERIFIED_PASS = "verified_pass"
    VERIFIED_FAIL = "verified_fail"
    UNVERIFIED = "unverified"
    MANUAL = "manual"
    BLOCKED = "blocked"
    OPTIONAL = "optional"


class EvidenceRef(BaseModel):
    kind: str
    source: str
    detail: str | None = None


class GateFinding(BaseModel):
    key: str
    kind: GateReasonKind
    title: str
    reason: str
    verdict_effect: VerdictEffect
    priority: ScenarioPriority | None = None
    scenario_key: str | None = None
    routes: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    verified: bool = False
    product_facing: bool = False
    failure_category: FailureCategory | None = None
    execution_run_id: str | None = None
    execution_step_indexes: list[int] = Field(default_factory=list)
    source_memory_keys: list[str] = Field(default_factory=list)
    source_rule_keys: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class CoverageItem(BaseModel):
    scenario_key: str
    title: str
    priority: ScenarioPriority
    required: bool
    required_reason: str | None = None
    readiness: AutomationReadiness
    execution_status: str | None = None
    verified: bool = False
    failure_category: FailureCategory | None = None
    coverage_outcome: CoverageOutcome
    routes: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    source_impact_keys: list[str] = Field(default_factory=list)
    historical_memory_keys: list[str] = Field(default_factory=list)
    historical_rule_keys: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    required_total: int = 0
    required_verified_pass: int = 0
    required_verified_fail: int = 0
    required_unverified: int = 0
    required_manual: int = 0
    required_blocked: int = 0
    optional_total: int = 0
    optional_verified: int = 0
    historical_required_total: int = 0
    historical_required_verified: int = 0
    truncated: bool = False
    has_coverage_gaps: bool = False


class HistoricalRisk(BaseModel):
    memory_key: str
    rule_key: str | None = None
    score: int
    reasons: list[str] = Field(default_factory=list)
    strong_match: bool = False
    related_scenario_keys: list[str] = Field(default_factory=list)
    covered: bool = False
    evidence: list[Evidence] = Field(default_factory=list)


class InputIntegrityFinding(BaseModel):
    kind: GateReasonKind = GateReasonKind.INPUT_INTEGRITY_GAP
    reason: str
    verdict_effect: VerdictEffect = VerdictEffect.MANUAL_REVIEW


class DecisionTraceEntry(BaseModel):
    rule_id: str
    reason: str
    scenario_key: str | None = None
    finding_key: str | None = None


class GateAIExplanation(BaseModel):
    summary: str
    grouped_reasons: list[str] = Field(default_factory=list)
    manual_review_checklist: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None


class GateMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    gate_version: str = GATE_VERSION
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    report_key: str
    project_source_id: str
    project_fingerprint: str
    change_source_id: str
    scenario_plan_key: str
    execution_run_id: str


class GateReport(BaseModel):
    metadata: GateMetadata
    verdict: GateVerdict
    confidence: GateConfidence
    headline: str
    blocking_findings: list[GateFinding] = Field(default_factory=list)
    manual_review_findings: list[GateFinding] = Field(default_factory=list)
    informational_findings: list[GateFinding] = Field(default_factory=list)
    coverage_summary: CoverageSummary = Field(default_factory=CoverageSummary)
    coverage_items: list[CoverageItem] = Field(default_factory=list)
    historical_risks: list[HistoricalRisk] = Field(default_factory=list)
    input_integrity_findings: list[InputIntegrityFinding] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    decision_trace: list[DecisionTraceEntry] = Field(default_factory=list)
    ai_explanation: GateAIExplanation | None = None


class GateInputBundle(BaseModel):
    project: ProjectKnowledge
    impact: ImpactReport
    scenario_plan: ScenarioPlan
    scenario_plan_key: str
    execution: "ExecutionReport"
    memory_recall: MemoryRecallResult | None = None


from qgate_browser_execution.models import ExecutionReport  # noqa: E402
