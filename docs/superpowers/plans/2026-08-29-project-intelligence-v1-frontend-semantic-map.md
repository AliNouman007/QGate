# Project Intelligence V1 Frontend/Semantic/Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Project Intelligence V1 with React/Next.js/TypeScript awareness, richer bounded semantic output, and a read-only dashboard Project Map backed by persisted knowledge.

**Architecture:** Keep deterministic analysis in `packages/project-intelligence`. Add evidence-backed framework facts and richer semantic models there. Expose persisted knowledge through a small authenticated API read model, then render it in the existing dashboard without adding a second scanner or allowing arbitrary browser-supplied filesystem paths.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, React 19, TypeScript strict, TanStack Router, existing API client/test stack.

**Spec:** `docs/superpowers/specs/2026-08-29-project-intelligence-v1-design.md`

## Global Constraints

- Remain general-purpose; no marketplace/business assumptions.
- Deterministic evidence is authoritative; semantic/AI classification only enriches it.
- No whole-repository LLM prompt.
- Do not modify target projects.
- Do not implement Impact Analysis in PR #1.
- No arbitrary filesystem path accepted from the browser.
- Every behavioral change gets tests and documentation.

---

### Task 1: Framework-aware knowledge models and extraction

**Files:**
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/models.py`
- Create: `packages/project-intelligence/src/qgate_project_intelligence/frameworks.py`
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/analyzer.py`
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/report.py`
- Test: `packages/project-intelligence/tests/test_project_intelligence.py`

**Interfaces:**
- Produces evidence-backed `FrameworkFact`, `RouteFact`, and symbol/component facts stored on `FileAnalysis` and summarized on `ProjectSummary`.

- [ ] Add failing tests for React component/hook/context detection, Next App/Pages routes, client/server directives, Next runtime APIs, and TypeScript declarations.
- [ ] Run focused tests and confirm failure for missing framework facts.
- [ ] Add minimal Pydantic models and pure framework extractor.
- [ ] Integrate extractor into per-file analysis without changing source ingestion.
- [ ] Extend summary/report with framework and route/component counts.
- [ ] Run focused tests until green.

### Task 2: Richer bounded semantic classification

**Files:**
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/semantic.py`
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/models.py`
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/analyzer.py`
- Test: `packages/project-intelligence/tests/test_project_intelligence.py`

**Interfaces:**
- Produces `semantic_states` in `ProjectKnowledge`; each classification contains label, kind, explanation, confidence, evidence, and runtime-verification flag.

- [ ] Add failing tests that evidence packs include framework context and semantic results never lose evidence.
- [ ] Add `SemanticStateKind` and richer `SemanticClassification` fields.
- [ ] Build packs from meaningful deterministic facts plus nearby framework facts only.
- [ ] Keep heuristic fallback deterministic and conservative; unknown/general facts require runtime verification when meaning is ambiguous.
- [ ] Store semantic classifications in `ProjectKnowledge`.
- [ ] Run focused tests until green.

### Task 3: Persisted knowledge listing and latest selection

**Files:**
- Modify: `packages/project-intelligence/src/qgate_project_intelligence/store.py`
- Test: `packages/project-intelligence/tests/test_project_intelligence.py`

**Interfaces:**
- Produces `JsonKnowledgeStore.list_projects()` and `JsonKnowledgeStore.latest()`.

- [ ] Add failing tests for multiple persisted projects and latest-by-analysis-time selection.
- [ ] Implement deterministic JSON enumeration; ignore invalid/non-knowledge JSON safely.
- [ ] Run focused tests until green.

### Task 4: Read-only Project Intelligence API

**Files:**
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/src/suitest_api/routers/project_intelligence.py`
- Modify: `apps/api/src/suitest_api/main.py`
- Create: `apps/api/tests/test_project_intelligence_api.py`

**Interfaces:**
- `GET /api/v1/project-intelligence/projects`
- `GET /api/v1/project-intelligence/latest`
- `GET /api/v1/project-intelligence/projects/{source_key}`

- [ ] Add API tests for authenticated list/latest/detail and empty-store 404 behavior.
- [ ] Add `qgate-project-intelligence` workspace dependency to API package.
- [ ] Use configured QGate knowledge directory; do not accept filesystem paths from requests.
- [ ] Register router in app factory.
- [ ] Run API tests until green.

### Task 5: Dashboard Project Map

**Files:**
- Create: `apps/web/src/components/dashboard/project-map.tsx`
- Modify: `apps/web/src/routes/_app/dashboard.tsx`
- Modify/Create test: `apps/web/src/routes/_app/dashboard.test.tsx`
- Modify mocks only if required by existing web test harness.

**Interfaces:**
- Dashboard fetches `/api/v1/project-intelligence/latest` and renders persisted knowledge summary.

- [ ] Add failing UI test for empty and populated Project Map states.
- [ ] Build compact Project Map card/section using existing tokens/components.
- [ ] Show languages/frameworks, routes/components, reused modules, behavioral/semantic states, evidence snippets, and coverage gaps.
- [ ] Treat 404 as “No project analyzed yet,” not an application error.
- [ ] Run dashboard tests/build until green.

### Task 6: Documentation and verification

**Files:**
- Modify: `docs/PROJECT_INTELLIGENCE.md`
- Modify: `QGATE_PROGRESS.md`
- Review: `docs/README.md`, `docs/API.md`, `.env.example` only if contracts/config require changes.

- [ ] Document framework facts, semantic state contract, persisted knowledge API, Project Map workflow, limitations, and local verification.
- [ ] Mark only genuinely implemented Project Intelligence items complete on the feature branch.
- [ ] Run package tests, API tests, web tests/build, Ruff, mypy, and affected root tests locally via Antigravity before merge.
- [ ] Keep PR #1 open and unmerged until verification is reviewed.
