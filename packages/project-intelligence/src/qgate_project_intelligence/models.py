from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.1"
ANALYZER_VERSION = "0.4.0"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FileRole(StrEnum):
    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    ROUTE = "route"
    COMPONENT = "component"
    SERVICE = "service"
    STATE = "state"
    OTHER = "other"


class FrameworkKind(StrEnum):
    REACT = "react"
    NEXTJS = "nextjs"
    TYPESCRIPT = "typescript"


class SymbolKind(StrEnum):
    COMPONENT = "component"
    HOOK = "hook"
    CONTEXT = "context"
    PROVIDER = "provider"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"


class BehaviorCategory(StrEnum):
    AUTH = "auth"
    PERMISSION = "permission"
    FEATURE_FLAG = "feature_flag"
    LOADING = "loading"
    ERROR = "error"
    EMPTY = "empty"
    STORAGE = "storage"
    RESPONSIVE = "responsive"
    GENERAL = "general"
    TECHNICAL_GUARD = "technical_guard"


class SemanticStateKind(StrEnum):
    USER_STATE = "user_state"
    ACCESS_STATE = "access_state"
    FEATURE_STATE = "feature_state"
    DATA_STATE = "data_state"
    VIEWPORT_STATE = "viewport_state"
    RUNTIME_STATE = "runtime_state"
    TECHNICAL = "technical"
    GENERAL = "general"


class AnalysisBudget(BaseModel):
    max_files: int = Field(default=10_000, ge=1)
    max_file_bytes: int = Field(default=512_000, ge=1)
    max_total_bytes: int = Field(default=100_000_000, ge=1)
    max_depth: int = Field(default=32, ge=1)


class Evidence(BaseModel):
    path: str
    line: int = Field(ge=1)
    excerpt: str
    kind: str


class ImportFact(BaseModel):
    module: str
    evidence: Evidence


class BehaviorFact(BaseModel):
    expression: str
    category: BehaviorCategory
    confidence: Confidence
    evidence: Evidence
    meaningful: bool


class FrameworkFact(BaseModel):
    framework: FrameworkKind
    feature: str
    value: str | None = None
    confidence: Confidence = Confidence.HIGH
    evidence: Evidence


class RouteFact(BaseModel):
    route: str
    router: str
    kind: str
    dynamic: bool = False
    evidence: Evidence


class SymbolFact(BaseModel):
    name: str
    kind: SymbolKind
    exported: bool = False
    evidence: Evidence


class FileRecord(BaseModel):
    path: str
    size_bytes: int = Field(ge=0)
    content_hash: str
    language: str | None = None
    role: FileRole = FileRole.OTHER


class FileAnalysis(BaseModel):
    record: FileRecord
    imports: list[ImportFact] = Field(default_factory=list)
    behaviors: list[BehaviorFact] = Field(default_factory=list)
    frameworks: list[FrameworkFact] = Field(default_factory=list)
    routes: list[RouteFact] = Field(default_factory=list)
    symbols: list[SymbolFact] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    source: str
    target: str
    module: str
    evidence: Evidence


class CoverageGap(BaseModel):
    path: str | None = None
    reason: str
    detail: str | None = None


class ProjectSummary(BaseModel):
    total_files: int = 0
    analyzed_files: int = 0
    total_source_bytes: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    frameworks: dict[str, int] = Field(default_factory=dict)
    declared_frameworks: list[str] = Field(default_factory=list)
    roles: dict[str, int] = Field(default_factory=dict)
    reused_modules: dict[str, int] = Field(default_factory=dict)
    behavioral_categories: dict[str, int] = Field(default_factory=dict)
    route_count: int = 0
    component_count: int = 0
    hook_count: int = 0


class AnalysisMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    analyzer_version: str = ANALYZER_VERSION
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_id: str
    source_fingerprint: str
    reused_files: int = 0
    analyzed_files: int = 0


class SemanticState(BaseModel):
    key: str
    label: str
    kind: SemanticStateKind
    explanation: str
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)
    needs_runtime_verification: bool = False


class ProjectKnowledge(BaseModel):
    metadata: AnalysisMetadata
    summary: ProjectSummary
    files: list[FileAnalysis]
    dependencies: list[DependencyEdge] = Field(default_factory=list)
    semantic_states: list[SemanticState] = Field(default_factory=list)
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
