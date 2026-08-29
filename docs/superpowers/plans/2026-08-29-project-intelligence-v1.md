# Project Intelligence V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete deterministic Project Intelligence V1 foundation as an isolated QGate workspace package.

**Architecture:** A dedicated `qgate-project-intelligence` Python package ingests local/ZIP sources, performs bounded static indexing and behavioral extraction, builds a dependency graph, exposes bounded semantic evidence packs, persists structured knowledge, supports incremental reuse, and renders a concise project map. It does not modify target repositories and does not require an LLM.

**Tech Stack:** Python 3.12, Pydantic v2, pathlib/zipfile/hashlib/json/regex from stdlib, pytest, existing uv monorepo tooling.

**Spec:** `docs/superpowers/specs/2026-08-29-project-intelligence-v1-design.md`

## Global Constraints

- Keep the core general-purpose; no marketplace-specific assumptions.
- Do not add a third-party parsing dependency in V1.
- Never modify the analyzed target project.
- All uncertainty/unsupported constructs must be represented explicitly as coverage gaps or low-confidence facts.
- Semantic classification consumes bounded evidence packs only.
- Tests and documentation are part of the feature.

---

### Task 1: Package skeleton and public models

**Files:**
- Create: `packages/project-intelligence/pyproject.toml`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/__init__.py`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/models.py`
- Create: `packages/project-intelligence/tests/test_models.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces `AnalysisBudget`, `Evidence`, `ImportFact`, `BehaviorFact`, `FileRecord`, `FileAnalysis`, `DependencyEdge`, `CoverageGap`, `ProjectSummary`, `AnalysisMetadata`, and `ProjectKnowledge`.

- [ ] Write tests that validate budget defaults, evidence serialization, and ProjectKnowledge round-trip.
- [ ] Run model tests and verify RED before implementation.
- [ ] Implement the minimal Pydantic models and package metadata.
- [ ] Add the package to uv workspace, mypy path, and pytest testpaths.
- [ ] Run model tests, ruff, and mypy for the package.

### Task 2: Source adapters and bounded inventory

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/source.py`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/scanner.py`
- Create: `packages/project-intelligence/tests/test_scanner.py`

**Interfaces:**
- Produces `ProjectSource`, `LocalPathSource`, `ZipProjectSource`, and `ProjectScanner.scan_inventory()`.

- [ ] Write fixture tests for ignored folders, source languages, file roles, byte/file/depth budgets, and ZIP ingestion.
- [ ] Verify RED.
- [ ] Implement read-only source adapters and bounded inventory scanning.
- [ ] Record coverage gaps for skipped binary/oversized/budget-limited content.
- [ ] Verify tests and static checks.

### Task 3: Per-file structural and behavioral extraction

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/extractors.py`
- Create: `packages/project-intelligence/tests/test_extractors.py`

**Interfaces:**
- Produces `analyze_text_file(record, text) -> FileAnalysis`.

- [ ] Write tests for Python imports, JS/TS imports, conditional branches, auth/permission, feature flags, loading/error/empty, storage, responsive signals, and technical guards.
- [ ] Verify RED.
- [ ] Implement conservative line-based extractors with evidence and explicit confidence.
- [ ] Verify tests and static checks.

### Task 4: Dependency graph and reuse detection

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/graph.py`
- Create: `packages/project-intelligence/tests/test_graph.py`

**Interfaces:**
- Produces `build_dependency_graph(files) -> list[DependencyEdge]` and reuse counts stored in project summary.

- [ ] Write tests for relative Python and JS/TS imports and shared module reuse.
- [ ] Verify RED.
- [ ] Implement deterministic import resolution against indexed paths.
- [ ] Verify tests and static checks.

### Task 5: Bounded semantic evidence packs

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/semantic.py`
- Create: `packages/project-intelligence/tests/test_semantic.py`

**Interfaces:**
- Produces `EvidencePack`, `SemanticClassification`, `SemanticClassifier` protocol, `HeuristicSemanticClassifier`, and `build_evidence_packs()`.

- [ ] Write tests showing packs are bounded and preserve evidence references/confidence.
- [ ] Verify RED.
- [ ] Implement deterministic V1 classifier and extension contract for future LLM-backed classifiers.
- [ ] Verify tests/static checks.

### Task 6: Analyzer orchestration, fingerprinting, and incremental reuse

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/analyzer.py`
- Create: `packages/project-intelligence/tests/test_analyzer.py`

**Interfaces:**
- Produces `ProjectIntelligenceAnalyzer.analyze(source, previous=None) -> ProjectKnowledge`.

- [ ] Write tests for end-to-end small fixture analysis, source fingerprint changes, unchanged file reuse, changed-file re-analysis, and removed files.
- [ ] Verify RED.
- [ ] Implement orchestration and incremental cache reuse based on content hashes/analyzer version.
- [ ] Rebuild project-level graph and summary after reused/new analyses are assembled.
- [ ] Verify tests/static checks.

### Task 7: Persistence, report, and CLI

**Files:**
- Create: `packages/project-intelligence/src/qgate_project_intelligence/store.py`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/report.py`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/cli.py`
- Create: `packages/project-intelligence/tests/test_store_report.py`
- Modify: `packages/project-intelligence/pyproject.toml`

**Interfaces:**
- Produces `JsonKnowledgeStore`, `render_project_map()`, and CLI `qgate-project-intelligence`.

- [ ] Write tests proving storage is caller-controlled/outside target, JSON round-trip works, and report contains routes/modules/states/gaps.
- [ ] Verify RED.
- [ ] Implement store/report/CLI.
- [ ] Verify tests/static checks.

### Task 8: Documentation and progress

**Files:**
- Create: `docs/PROJECT_INTELLIGENCE.md`
- Modify: `docs/README.md`
- Modify: `QGATE_PROGRESS.md`

- [ ] Document business workflow, architecture, inputs/outputs, scaling model, evidence/confidence, incremental analysis, CLI usage, limitations, and future extension points.
- [ ] Link subsystem docs from docs index.
- [ ] Mark only capabilities actually implemented in the branch as complete in progress tracker.
- [ ] Confirm no Impact Analysis/Scenario Intelligence implementation leaked into this branch.

### Task 9: Branch verification and PR

- [ ] Run package tests and the existing default non-E2E suite if the environment permits.
- [ ] Run ruff and mypy on changed Python source.
- [ ] Review diff for unrelated changes.
- [ ] Open PR from `feat/project-intelligence-v1` to `main` without merging.
- [ ] Record exact verification limitations for local Antigravity follow-up.
