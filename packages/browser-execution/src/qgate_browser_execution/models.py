from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.1"
RUNNER_VERSION = "0.2.0"


class OperationKind(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_HIDDEN = "assert_hidden"
    ASSERT_TEXT = "assert_text"
    ASSERT_VALUE = "assert_value"
    ASSERT_URL = "assert_url"
    ASSERT_ATTRIBUTE = "assert_attribute"
    ASSERT_LAYOUT_STATE = "assert_layout_state"
    CAPTURE = "capture"
    COMPARE_STATE = "compare_state"


class ExecutionStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    EXECUTION_ERROR = "execution_error"
    UNVERIFIED = "unverified"
    SKIPPED_MANUAL = "skipped_manual"
    BLOCKED = "blocked"


class FailureCategory(StrEnum):
    ASSERTION_FAILURE = "assertion_failure"
    NAVIGATION_FAILURE = "navigation_failure"
    STATE_SETUP_FAILURE = "state_setup_failure"
    TARGET_RESOLUTION_FAILURE = "target_resolution_failure"
    TEST_DEFINITION_ERROR = "test_definition_error"
    ENVIRONMENT_FAILURE = "environment_failure"
    BROWSER_FAILURE = "browser_failure"
    NETWORK_INFRA_FAILURE = "network_infra_failure"
    TIMEOUT = "timeout"
    UNKNOWN_EXECUTION_FAILURE = "unknown_execution_failure"


class ExecutionConfig(BaseModel):
    base_url: str
    browser: str = "chromium"
    headed: bool = False
    global_timeout_ms: int = Field(default=45_000, ge=1_000, le=300_000)
    step_timeout_ms: int = Field(default=10_000, ge=500, le=120_000)
    retry_budget: int = Field(default=1, ge=0, le=1)
    screenshot_on_failure: bool = True
    capture_console: bool = True
    capture_network: bool = True
    artifact_dir: str = "~/.qgate/browser-execution/artifacts"


class TargetHint(BaseModel):
    role: str | None = None
    name: str | None = None
    label: str | None = None
    test_id: str | None = None
    text: str | None = None
    selector: str | None = None
    attribute: str | None = None
    expected_value: str | None = None


class CompiledStep(BaseModel):
    index: int
    operation: OperationKind
    source_action: str
    source_expected: str
    route: str | None = None
    target: TargetHint | None = None
    value: str | None = None
    expected: str | None = None
    required: bool = True
    state_setup: bool = False


class CompiledScenario(BaseModel):
    scenario_key: str
    pass_key: str | None = None
    state_key: str | None = None
    state_label: str | None = None
    title: str
    kind: str
    priority: str
    route: str | None = None
    steps: list[CompiledStep] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    source_impact_keys: list[str] = Field(default_factory=list)


class PreclassifiedScenario(BaseModel):
    scenario_key: str
    title: str
    status: ExecutionStatus
    reason: str


class ExecutionRequest(BaseModel):
    scenario_plan_key: str
    project_source_id: str
    project_fingerprint: str
    impact_change_source_id: str
    config: ExecutionConfig
    scenarios: list[CompiledScenario] = Field(default_factory=list)
    preclassified: list[PreclassifiedScenario] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    kind: str
    path: str
    sha256: str | None = None


class ConsoleEvidence(BaseModel):
    level: str
    message: str
    source: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NetworkEvidence(BaseModel):
    method: str
    url: str
    resource_type: str | None = None
    status: int | None = None
    failure: str | None = None
    duration_ms: float | None = None


class DomEvidence(BaseModel):
    locator_description: str | None = None
    tag: str | None = None
    role: str | None = None
    name: str | None = None
    text: str | None = None
    value: str | None = None
    visible: bool | None = None
    enabled: bool | None = None
    checked: bool | None = None
    selected: bool | None = None
    html_excerpt: str | None = None
    bounding_box: dict[str, float] | None = None
    computed_css: dict[str, str] = Field(default_factory=dict)


class StepEvidence(BaseModel):
    requested_route: str | None = None
    final_url: str | None = None
    title: str | None = None
    dom: DomEvidence | None = None
    console: list[ConsoleEvidence] = Field(default_factory=list)
    network: list[NetworkEvidence] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class StepExecution(BaseModel):
    index: int
    operation: OperationKind
    source_action: str
    source_expected: str
    status: ExecutionStatus
    failure_category: FailureCategory | None = None
    actual: str | None = None
    expected: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    detail: str | None = None
    evidence: StepEvidence = Field(default_factory=StepEvidence)


class AttemptRecord(BaseModel):
    attempt: int
    status: ExecutionStatus
    failure_category: FailureCategory | None = None
    reason: str | None = None


class ScenarioExecution(BaseModel):
    scenario_key: str
    title: str
    kind: str
    priority: str
    status: ExecutionStatus
    failure_category: FailureCategory | None = None
    verified: bool = False
    target_route: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    steps: list[StepExecution] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    detail: str | None = None
    source_impact_keys: list[str] = Field(default_factory=list)


class ExecutionCoverageGap(BaseModel):
    scenario_key: str | None = None
    reason: str
    detail: str | None = None


class ExecutionSummary(BaseModel):
    selected: int = 0
    executed: int = 0
    passed: int = 0
    failed: int = 0
    execution_error: int = 0
    unverified: int = 0
    skipped_manual: int = 0
    blocked: int = 0


class ExecutionMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    runner_version: str = RUNNER_VERSION
    run_id: str
    scenario_plan_key: str
    project_source_id: str
    project_fingerprint: str
    impact_change_source_id: str
    config_fingerprint: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class ExecutionReport(BaseModel):
    metadata: ExecutionMetadata
    summary: ExecutionSummary
    scenarios: list[ScenarioExecution] = Field(default_factory=list)
    coverage_gaps: list[ExecutionCoverageGap] = Field(default_factory=list)
    run_artifacts: list[ArtifactRef] = Field(default_factory=list)
