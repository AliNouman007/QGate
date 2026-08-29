# Impact Analysis V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one complete Impact Analysis V1 feature that turns a local Git/patch change into an evidence-backed `ImpactReport` by reusing Project Intelligence, then exposes persisted results through CLI, local API, and dashboard.

**Architecture:** Add a dedicated `qgate-impact-analysis` workspace package. The package normalizes change sources into `ChangeSet`, maps changes to `ProjectKnowledge`, traverses existing dependency/reuse data, emits deterministic impact items, persists reports, and provides a CLI. Optional AI enrichment lives in the existing agent layer and receives only bounded impact evidence packs. The API/dashboard read persisted reports only and never accept arbitrary filesystem paths.

**Tech Stack:** Python 3.12, Pydantic, subprocess/git, existing `qgate-project-intelligence`, FastAPI, React 19, TypeScript, TanStack Router/Query, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-impact-analysis-v1-design.md`

## Global Constraints

- Diff is the source of truth for what changed.
- `ProjectKnowledge` is the source of truth for known structure/state; do not rebuild Project Intelligence.
- AI is optional, bounded, evidence-preserving, and may not add unsupported targets or raise confidence.
- Every impact item carries level, reason, confidence, evidence, categories, and runtime-verification status.
- Traversal must be bounded and cycle-safe.
- Target repositories remain read-only.
- Missing/stale knowledge and unsupported diff constructs are surfaced, never guessed away.
- Scenario generation, browser execution, final gate decisions, QA memory, and auto-fixes are out of scope.

---

### Task 1: Impact models, diff parsing, and change-source contracts

**Files:**
- Create: `packages/impact-analysis/pyproject.toml`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/__init__.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/models.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/diff_parser.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/source.py`
- Test: `packages/impact-analysis/tests/test_change_sources.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces `ChangeSet`, `ChangedFile`, `DiffHunk`, `ChangedLineRange`, `ChangeSource`, `UnifiedDiffSource`, `LocalGitSource`.
- `LocalGitSource(repo_path, base_ref="main", head_ref="HEAD").load() -> ChangeSet`.
- `UnifiedDiffSource(text, metadata=None).load() -> ChangeSet`.

- [ ] Write failing tests for Git-style unified patches: modified/added/deleted/renamed files, hunk ranges, additions/deletions, malformed/unsupported lines producing parse gaps.
- [ ] Run the focused tests and confirm failure.
- [ ] Implement models and a conservative unified-diff parser.
- [ ] Implement local Git source using `git diff --no-ext-diff --unified=3 <base>...<head>` plus `git diff --name-status -M` without modifying the repository.
- [ ] Add the new package to the uv workspace and mypy paths/sources following existing repo conventions.
- [ ] Run focused tests.

### Task 2: Change mapping, classification, and deterministic blast-radius engine

**Files:**
- Create: `packages/impact-analysis/src/qgate_impact_analysis/classifier.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/mapping.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/engine.py`
- Test: `packages/impact-analysis/tests/test_engine.py`

**Interfaces:**
- Produces `ImpactAnalyzer(project_knowledge, limits=None).analyze(change_set) -> ImpactReport`.
- Produces deterministic categories and impact items with `DIRECT`, `INDIRECT`, `POSSIBLE`, `UNKNOWN` levels.

- [ ] Write failing fixture tests for changed-symbol overlap, file-level fallback, deterministic change categories, direct impacts, reverse-dependency paths, cycles, traversal depth/node limits, reused modules, affected routes, relevant states, and unrelated-route exclusion.
- [ ] Run focused tests and confirm failure.
- [ ] Implement conservative symbol mapping by exact path + hunk/evidence-line proximity only.
- [ ] Implement deterministic change classification from file role/framework/behavior/path/extension/changed-line signals.
- [ ] Implement bounded reverse-dependency traversal over existing `ProjectKnowledge.dependencies` with explicit dependency paths.
- [ ] Implement route/state/shared-reuse derivation and coverage gaps/runtime-verification flags.
- [ ] Run focused tests.

### Task 3: Persistence, human-readable report, and CLI

**Files:**
- Create: `packages/impact-analysis/src/qgate_impact_analysis/store.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/report.py`
- Create: `packages/impact-analysis/src/qgate_impact_analysis/cli.py`
- Test: `packages/impact-analysis/tests/test_store_cli.py`

**Interfaces:**
- `JsonImpactStore(root).save(report)`, `.latest()`, `.list_reports()`, `.load_key(key)`.
- CLI supports local Git comparison and supplied patch input, explicit ProjectKnowledge file/store selection, `--json`, bounded traversal options, and QGate-owned persistence.

- [ ] Write failing tests for stable report keys, save/load/list/latest, ProjectKnowledge fingerprint metadata, readable report sections, missing knowledge errors, and patch/local-git CLI argument parsing.
- [ ] Run focused tests and confirm failure.
- [ ] Implement store/report/CLI minimally.
- [ ] Ensure default storage is outside the target repo (`~/.qgate/impact-analysis`).
- [ ] Run focused tests.

### Task 4: Optional bounded AI impact enrichment

**Files:**
- Create: `packages/agent/src/suitest_agent/impact_analysis_semantic.py`
- Test: `packages/agent/tests/test_impact_analysis_semantic.py`
- Modify: `packages/agent/pyproject.toml`

**Interfaces:**
- `build_impact_evidence_packs(report, max_items_per_pack, max_packs)` in core package.
- `enrich_impact_report(provider, model, report) -> ImpactReport` in agent layer.

- [ ] Write failing tests proving bounded packs, evidence preservation, no new target keys, confidence clamping, runtime-verification monotonicity, and malformed/provider failure fallback.
- [ ] Run focused tests and confirm failure.
- [ ] Implement bounded pack creation in the impact package.
- [ ] Implement provider-backed enrichment using existing `LLMProvider`, structured JSON validation, and deterministic fallback.
- [ ] Run focused tests.

### Task 5: Local read-only API

**Files:**
- Create: `apps/api/src/suitest_api/routers/impact_analysis.py`
- Create: `apps/api/tests/test_impact_analysis_api.py`
- Modify: `apps/api/src/suitest_api/routers/projects.py`
- Modify: `apps/api/src/suitest_api/settings.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `.env.example`
- Modify: `docs/API.md`

**Interfaces:**
- `GET /api/v1/impact-analysis/reports`
- `GET /api/v1/impact-analysis/latest`
- `GET /api/v1/impact-analysis/reports/{key}`

- [ ] Write failing API tests for local authenticated list/latest/detail, empty store, invalid key, and server-mode 404.
- [ ] Run focused tests and confirm failure.
- [ ] Implement settings/store wiring and read-only router using normal workspace auth.
- [ ] Register the router with only minimal changes to existing router composition.
- [ ] Document API/environment configuration.
- [ ] Run focused tests.

### Task 6: Impact dashboard view

**Files:**
- Create: `apps/web/src/hooks/use-impact-analysis.ts`
- Create: `apps/web/src/routes/_app/impact.tsx`
- Create: `apps/web/src/routes/_app/impact.test.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Generated during local verification: `apps/web/src/routeTree.gen.ts`

**Interfaces:**
- `/impact` displays the latest persisted ImpactReport.
- 404/latest-empty maps to a developer-friendly empty state, not an application error.

- [ ] Write failing web tests for empty and populated Impact views.
- [ ] Run focused tests and confirm failure.
- [ ] Implement query hook and dashboard sections for changed files/symbols, direct/indirect impacts, affected routes/states, shared blast radius, confidence/reasons, runtime warnings, and coverage gaps.
- [ ] Add one minimal sidebar nav item.
- [ ] Run focused tests; route-tree regeneration/build is deferred to local Antigravity verification.

### Task 7: End-to-end fixture validation and maintained docs

**Files:**
- Create: `packages/impact-analysis/tests/test_frontend_integration.py`
- Create: `docs/IMPACT_ANALYSIS.md`
- Modify: `docs/README.md`
- Modify: `QGATE_PROGRESS.md` only to record implementation-in-PR status, not merged completion.

**Interfaces:**
- Temporary React/Next/TypeScript git fixture: Project Intelligence baseline -> commit -> change reused component -> local Git ChangeSet -> ImpactReport.

- [ ] Write integration test proving changed shared component, reverse dependents, affected routes/states, shared group, unrelated-route exclusion, and persistence/reload.
- [ ] Add styling-only, route/auth-state, deletion/rename, and unknown/dynamic-dependency regression coverage where deterministic support exists.
- [ ] Run focused integration tests.
- [ ] Write `docs/IMPACT_ANALYSIS.md` with business workflow, architecture, contracts, limitations, CLI/API/dashboard usage, and relationship to Scenario Intelligence.
- [ ] Update docs index/progress tracker without marking Phase 2 merged/completed yet.

### Task 8: PR completion and verification handoff

**Files:**
- PR metadata only; local verifier may update `uv.lock`, generated route tree, formatting/type fixes, or tests if required.

- [ ] Review full branch diff against `main` for unrelated changes.
- [ ] Open one PR titled `feat: Impact Analysis V1` from `feat/impact-analysis-v1` to `main`.
- [ ] Record static verification limitations honestly; do not claim local runtime tests from GitHub-only execution.
- [ ] Provide Antigravity a focused local verification/repair prompt covering uv lock, route generation, core/agent/API/web tests, ruff, mypy, build, realistic local Git fixture, false-positive exclusion, traversal bounds, and dashboard visual smoke.
- [ ] Do not merge until Antigravity verification is returned and independently reviewed.
