# QGate Simple UX V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make QGate's default UI follow one obvious project-scoped flow: Add/Select Project → Analyze → Test Cases/Scenarios → Run → Result.

**Architecture:** Reuse existing Suitest/QGate routes and APIs. Simplify navigation, enforce selected-project scoping for intelligence surfaces, and surface existing analysis/generation/run actions in the normal UI. Hide/demote technical/demo surfaces instead of deleting subsystems.

**Tech Stack:** React 19, TypeScript, TanStack Router/Query, existing FastAPI QGate endpoints.

**Spec:** `docs/superpowers/specs/2026-08-30-qgate-simple-ux-v1-design.md`

## Global Constraints

- Stop immediately once acceptance criteria pass.
- No workspace architecture rewrite.
- No AI subsystem rewrite.
- No browser-only autonomous scenario generator.
- No broad visual redesign.
- No unrelated refactors or cleanup.
- Selected project must be the source of truth for every project-specific view.

---

### Task 1: Simplify shell navigation and local-mode workspace noise

**Files:**
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.test.tsx`
- Modify only if needed for local-mode signal: `apps/web/src/routes/_app.tsx`

**Produces:** A minimal primary sidebar and a non-confusing local-auth workspace presentation.

- [ ] Write failing sidebar tests for the simplified primary navigation.
- [ ] Verify tests fail against current sidebar.
- [ ] Keep primary destinations: Dashboard/Project Overview, Test Cases, Test Runs, Defects.
- [ ] Remove Project Map, Impact Analysis, Browser Execution, QA Memory, Final Gate, Analytics, Traceability, Eval from the primary rail; keep underlying routes intact.
- [ ] Keep Scenarios reachable from the testing flow rather than as unexplained primary navigation. If an explicit secondary/advanced affordance is necessary, keep it compact.
- [ ] In local-auth mode, hide/demote irrelevant workspace picker behavior so seeded E2E demo names are not presented as the normal project workflow. Do not delete workspace records.
- [ ] Run sidebar/layout tests.
- [ ] Commit.

### Task 2: Enforce selected-project scoping for Project Intelligence / scenarios

**Files:**
- Modify: `apps/web/src/hooks/use-project-intelligence.ts`
- Modify: `apps/web/src/routes/_app/project-map.tsx`
- Modify: `apps/web/src/routes/_app/scenarios.tsx`
- Modify: `apps/web/src/routes/_app/impact.tsx` only if its current request is also global/stale.
- Modify as required: `apps/api/src/suitest_api/routers/project_intelligence.py`
- Modify as required: `apps/api/src/suitest_api/routers/scenario_intelligence.py`
- Modify as required: `apps/api/src/suitest_api/routers/impact_analysis.py`
- Tests: matching web route/hook tests and focused API router tests.

**Produces:** No stale cross-project intelligence is shown after switching projects.

- [ ] Write failing regression test: select Project B after Project A has persisted intelligence; Project B must not render Project A routes/states.
- [ ] Confirm current `useLatestProjectIntelligence()` is globally keyed and `/project-intelligence/latest` can return unrelated persisted analysis.
- [ ] Add the smallest project-scoping contract using the existing active `projectId` and project/source identity. Prefer a project query parameter or project-specific lookup over new storage architecture.
- [ ] Include `projectId` in React Query keys so project switches invalidate/change the correct cache entry.
- [ ] If a selected project has no matching analysis, return/show `No project analyzed yet` with an Analyze action; never fall back to global latest/demo data.
- [ ] Apply the same selected-project rule to Scenarios and Impact Analysis only where their current APIs have the same stale-global behavior.
- [ ] Verify `qgate-test-shop` cannot display `/admin`, `/category`, `/search` unless those routes exist in its own analysis.
- [ ] Run focused API + web tests.
- [ ] Commit.

### Task 3: Make Project Overview the obvious Analyze entry point

**Files:**
- Modify: `apps/web/src/routes/_app/dashboard.tsx` (or the smallest existing overview surface)
- Reuse: `apps/web/src/routes/_app/project-map.tsx`
- Reuse existing Project Intelligence API; only modify API if UI-triggered analysis does not yet exist and an existing supported operation can be exposed safely.
- Tests: `apps/web/src/routes/_app/dashboard.test.tsx` plus focused API test if needed.

**Produces:** A selected project clearly shows its identity, analysis state, and a single Analyze Project action.

- [ ] Add failing tests for selected-project identity and Analyze/Analyzed state.
- [ ] Show selected project name/path prominently.
- [ ] If no matching project intelligence exists, show one obvious `Analyze Project` action rather than CLI instructions.
- [ ] Reuse existing analysis machinery; do not create another analyzer.
- [ ] After analysis, show a compact summary (files/routes/components/states) and a `View Project Map` secondary action.
- [ ] Run tests.
- [ ] Commit.

### Task 4: Clarify Test Cases / AI Generate / Scenarios flow

**Files:**
- Modify: `apps/web/src/routes/_app/cases.tsx`
- Modify only as needed: `apps/web/src/components/cases/GenerateModal.tsx`
- Modify only as needed: `apps/web/src/components/cases/CreateCaseDialog.tsx`
- Tests: existing cases/generate modal tests.

**Produces:** Manual creation and AI generation are obvious and project-scoped.

- [ ] Write failing tests that selected project context is used for manual/AI test generation.
- [ ] Keep `New case` and `Generate with AI` as the two primary actions.
- [ ] Add concise copy linking generated scenarios to the selected project; do not expose internal pipeline jargon unless in details.
- [ ] If LLM generation is unavailable/misconfigured, show a clear actionable error/status; do not silently fall back to unrelated demo content.
- [ ] Keep Scenario review reachable from this testing surface if existing routes support it; do not build a new scenario subsystem.
- [ ] Run cases/generation tests.
- [ ] Commit.

### Task 5: Demote Browser Execution into run details and verify end-to-end UI

**Files:**
- Modify only if needed: `apps/web/src/routes/_app/runs.tsx`
- Modify only if needed: run detail components under `apps/web/src/components/runs/`
- Keep `apps/web/src/routes/_app/execution.tsx` routable but not primary navigation.

**Produces:** Normal user sees run status/result first; technical execution details are drill-down.

- [ ] Verify a user can run a manual test and see result from Test Cases/Test Runs without visiting Browser Execution directly.
- [ ] If necessary, add a small `View execution details` link from a run result to existing evidence UI.
- [ ] Do not redesign the execution engine or evidence model.
- [ ] Run relevant web tests.
- [ ] Perform one visible browser validation using `qgate-test-shop`:
  `Select project → Analyze → verify project-only map → create/generate test → run → result`.
- [ ] Confirm demo workspace noise is no longer part of the normal local workflow.
- [ ] Confirm no stale project routes leak after switching projects.
- [ ] Run web test suite plus relevant API tests, lint/type checks already standard for repo.
- [ ] STOP when acceptance criteria pass. Do not add further hardening.
