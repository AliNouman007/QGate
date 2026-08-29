from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from qgate_project_intelligence.models import Confidence, Evidence

SCHEMA_VERSION = "1.0"
ANALYZER_VERSION = "0.1.0"


class ChangeSourceKind(StrEnum):
    LOCAL_GIT = "local_git"
    UNIFIED_DIFF = "unified_diff"
    GITHUB_PR = "github_pr"


class FileChangeStatus(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ChangeCategory(StrEnum):
    UI = "ui"
    STYLING = "styling"
    STATE = "state"
    ROUTING = "routing"
    API = "api"
    AUTH = "auth"
    FEATURE_FLAG = "feature_flag"
    STORAGE = "storage"
    RESPONSIVE = "responsive"
    SHARED = "shared"
    CONFIG = "config"
    TEST = "test"
    GENERAL = "general"


class ImpactLevel(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class ImpactTargetType(StrEnum):
    FILE = "file"
    SYMBOL = "symbol"
    COMPONENT = "component"
    ROUTE = "route"
    STATE = "state"
    MODULE = "module"


class ChangedLineRange(BaseModel):
    start: int = Field(ge=0)
    count: int = Field(default=1, ge=0)

    @property
    def end(self) -> int:
        if self.count == 0:
            return self.start
        return self.start + self.count - 1


class DiffHunk(BaseModel):
    old_range: ChangedLineRange
    new_range: ChangedLineRange
    header: str
    excerpt: str


class ChangedFile(BaseModel):
    path: str
    status: FileChangeStatus
    old_path: str | None = None
    hunks: list[DiffHunk] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    categories: list[ChangeCategory] = Field(default_factory=list)


class ChangeGap(BaseModel):
    path: str | None = None
    reason: str
    detail: str | None = None


class ChangeSet(BaseModel):
    source_kind: ChangeSourceKind
    source_id: str
    base_ref: str | None = None
    head_ref: str | None = None
    title: str | None = None
    url: str | None = None
    files: list[ChangedFile] = Field(default_factory=list)
    gaps: list[ChangeGap] = Field(default_factory=list)


class ChangedSymbol(BaseModel):
    file_path: str
    symbol_name: str
    symbol_kind: str
    confidence: Confidence
    evidence: Evidence


class DependencyStep(BaseModel):
    source: str
    target: str
    module: str


class ImpactItem(BaseModel):
    key: str
    target_type: ImpactTargetType
    target: str
    level: ImpactLevel
    reason: str
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)
    dependency_path: list[DependencyStep] = Field(default_factory=list)
    categories: list[ChangeCategory] = Field(default_factory=list)
    needs_runtime_verification: bool = False
    explanation: str | None = None
    priority_hint: str | None = None


class SharedImpactGroup(BaseModel):
    changed_target: str
    reuse_count: int
    affected_files: list[str] = Field(default_factory=list)
    affected_routes: list[str] = Field(default_factory=list)


class ImpactCoverageGap(BaseModel):
    path: str | None = None
    reason: str
    detail: str | None = None
    needs_runtime_verification: bool = True


class ImpactSummary(BaseModel):
    changed_files: int = 0
    changed_symbols: int = 0
    direct_impacts: int = 0
    indirect_impacts: int = 0
    possible_impacts: int = 0
    unknown_impacts: int = 0
    affected_routes: int = 0
    affected_states: int = 0
    runtime_verification_items: int = 0


class ImpactMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    analyzer_version: str = ANALYZER_VERSION
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_source_id: str
    project_fingerprint: str
    change_source_id: str


class ImpactReport(BaseModel):
    metadata: ImpactMetadata
    change_set: ChangeSet
    summary: ImpactSummary
    changed_symbols: list[ChangedSymbol] = Field(default_factory=list)
    direct_impacts: list[ImpactItem] = Field(default_factory=list)
    indirect_impacts: list[ImpactItem] = Field(default_factory=list)
    possible_impacts: list[ImpactItem] = Field(default_factory=list)
    unknown_impacts: list[ImpactItem] = Field(default_factory=list)
    affected_routes: list[ImpactItem] = Field(default_factory=list)
    affected_states: list[ImpactItem] = Field(default_factory=list)
    shared_groups: list[SharedImpactGroup] = Field(default_factory=list)
    coverage_gaps: list[ImpactCoverageGap] = Field(default_factory=list)
