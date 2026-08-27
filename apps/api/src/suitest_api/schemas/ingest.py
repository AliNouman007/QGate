"""Request/response schemas for the lifecycle ingest endpoints (Phase 2).

The Suitest lifecycle (``suitest test``) executes tests itself. Cases are
published before execution and results can be appended per test, then finalized;
legacy clients may still publish a completed run in one request. There is no ARQ
execution on this path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from suitest_shared.domain.enums import TestingApproach, TestLevel


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# --------------------------------------------------------------------------- #
# bulk-import (cases + steps)
# --------------------------------------------------------------------------- #
class IngestStep(_Camel):
    order: int
    action: str
    expected: str
    code: str | None = None


class IngestCase(_Camel):
    source_ref: str = Field(alias="sourceRef")
    # ``name`` is the legacy/compat field (historically the generated function
    # slug). Publishers SHOULD also send ``title`` (human display title) and
    # ``slug`` (technical key); when absent the service derives them from
    # ``name`` server-side — the frontend never humanizes.
    name: str
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    preconditions: str | None = None
    # Origin of the case. Lifecycle/MCP publishers send "MCP"; generic importers
    # (TestRail, JIRA, file) omit it and fall back to IMPORT. Any unknown value
    # also degrades to IMPORT so the enum stays authoritative.
    source: str | None = None
    priority: str = "P2"  # P1 | P2 | P3
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    automation_file_path: str | None = Field(default=None, alias="automationFilePath")
    automation_code: str | None = Field(default=None, alias="automationCode")
    generated_by: str | None = Field(default=None, alias="generatedBy")
    testing_approach: TestingApproach | None = Field(default=None, alias="testingApproach")
    test_level: TestLevel | None = Field(default=None, alias="testLevel")
    framework: str | None = None
    strategy_id: str | None = Field(default=None, alias="strategyId")
    strategy_ref: str | None = Field(default=None, alias="strategyRef")
    steps: list[IngestStep] = Field(default_factory=list)


class BulkImportBody(_Camel):
    # Either an explicit project id, or a slug (+ display name) the server
    # resolves/creates in the caller's workspace — publishers like the blackbox
    # pipeline have credentials but no project yet.
    project_id: str = Field(default="", alias="projectId")
    project_slug: str = Field(default="", alias="projectSlug")
    project_name: str = Field(default="", alias="projectName")
    suite_name: str = Field(alias="suiteName")
    mode: str = "backend"  # backend | frontend | desktop -> target_kind / provider defaults
    # Overrides the mode's default provider. A desktop suite needs it: FE_DESKTOP
    # defaults to screen-level automation, while a Slint or Electron app is
    # driven through its own bridge.
    mcp_provider: str = Field(default="", alias="mcpProvider")
    cases: list[IngestCase] = Field(default_factory=list)
    # Retest change-detection: mark MCP-sourced cases in this suite that the
    # current generation no longer produced as STALE (re-import reactivates).
    mark_stale: bool = Field(default=False, alias="markStale")


class ImportedCase(_Camel):
    source_ref: str = Field(alias="sourceRef")
    case_id: str = Field(alias="caseId")
    public_id: str = Field(alias="publicId")
    created: bool


class BulkImportResult(_Camel):
    suite_id: str = Field(alias="suiteId")
    # Resolved target project — lets a slug-publishing client persist the id
    # into its config so the next run is an explicit-id retest.
    project_id: str = Field(default="", alias="projectId")
    imported: list[ImportedCase] = Field(default_factory=list)
    # Public ids of cases newly marked STALE (markStale=true only).
    stale: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# project binding resolve/repair (publisher-facing, API-key auth)
# --------------------------------------------------------------------------- #
class ResolveProjectBody(_Camel):
    project_id: str = Field(default="", alias="projectId")
    project_slug: str = Field(default="", alias="projectSlug")
    project_name: str = Field(default="", alias="projectName")


class ProjectCandidate(_Camel):
    id: str
    slug: str
    name: str


class ResolveProjectResult(_Camel):
    # valid    — projectId exists in the caller's workspace
    # repaired — id missing/stale but exactly one project matched slug/name
    # missing  — no (unambiguous) match; caller must fail or explicitly recreate
    status: str
    project_id: str = Field(default="", alias="projectId")
    matched_by: str = Field(default="", alias="matchedBy")  # id | slug | name
    candidates: list[ProjectCandidate] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# runs/ingest (completed run)
# --------------------------------------------------------------------------- #
class IngestRunStep(_Camel):
    order: int
    type: str = "action"
    description: str = Field(default="", max_length=16_384)
    outcome: str = "PASSED"  # PASSED | FAILED | SKIPPED | ERROR
    duration_ms: int | None = Field(default=None, alias="durationMs")
    screenshot: str = Field(default="", max_length=4_096)
    screenshot_size_bytes: int = Field(default=0, alias="screenshotSizeBytes")


class IngestArtifact(_Camel):
    kind: str = Field(max_length=64)  # VIDEO | SCREENSHOT | CONSOLE_LOG | ...
    url: str = Field(max_length=4_096)  # file:// or s3:// already-resolved location
    mime_type: str = Field(default="application/octet-stream", alias="mimeType", max_length=255)
    size_bytes: int = Field(default=0, alias="sizeBytes")


class IngestResult(_Camel):
    name: str = Field(default="", max_length=255)
    slug: str = Field(default="", max_length=255)
    source_ref: str = Field(default="", alias="sourceRef", max_length=2_048)
    outcome: str = Field(default="PASSED", max_length=32)
    duration_ms: int = Field(default=0, alias="durationMs")
    error: str = Field(default="", max_length=1_000_000)
    # Structured failure class from the lifecycle classifier (selector_changed,
    # endpoint_not_found, auth_failure, …). Stored in run_step.state_snapshot.
    failure_kind: str = Field(default="", alias="failureKind", max_length=128)
    stdout: str = Field(default="", max_length=1_000_000)
    stderr: str = Field(default="", max_length=1_000_000)
    steps: list[IngestRunStep] = Field(default_factory=list, max_length=500)
    artifacts: list[IngestArtifact] = Field(default_factory=list, max_length=100)


class RunIngestBody(_Camel):
    # Empty on the first request: the server creates a RUNNING run. Publishers
    # can then send one result at a time with the returned id, keeping a single
    # run in the UI without retaining every artifact locally until suite end.
    # Older publishers omit both fields and retain the original single-shot
    # behaviour (create + append all results + finalize in one request).
    run_id: str = Field(default="", alias="runId")
    finalize: bool = True
    project_id: str = Field(default="", alias="projectId")
    project_slug: str = Field(default="", alias="projectSlug")
    project_name: str = Field(default="", alias="projectName")
    suite_name: str = Field(alias="suiteName")
    name: str
    env: str = "staging"
    branch: str | None = None
    commit_sha: str | None = Field(default=None, alias="commitSha")
    coverage_summary: dict[str, object] | None = Field(default=None, alias="coverageSummary")
    results: list[IngestResult] = Field(default_factory=list, max_length=500)


class RunIngestResult(_Camel):
    run_id: str = Field(alias="runId")
    project_id: str = Field(default="", alias="projectId")
    status: str
    total: int
    passed: int
    failed: int
