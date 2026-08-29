# Scenario Intelligence V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic-first Scenario Intelligence subsystem that converts matching `ProjectKnowledge` + `ImpactReport` into a prioritized, evidence-backed, persisted `ScenarioPlan` suitable for later Suitest/Playwright execution.

**Architecture:** Add a new `packages/scenario-intelligence` workspace package. It consumes existing Project Intelligence and Impact Analysis contracts, generates bounded scenario candidates, collapses duplicates, scores priority/readiness, and optionally allows bounded AI wording/prioritization enrichment through the existing agent provider boundary. Local API/dashboard only read persisted plans; they never accept arbitrary target paths.

**Tech Stack:** Python 3.12, Pydantic v2, existing qgate-project-intelligence/qgate-impact-analysis packages, existing Suitest agent provider abstraction, FastAPI, React 19 + TanStack Router + TypeScript, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-scenario-intelligence-v1-design.md`

## Global Constraints

- Structured scenarios only; no raw Playwright/Selenium code in this phase.
- Deterministic evidence is source of truth; AI is optional and bounded.
- Project fingerprint/source mismatch must fail clearly; never mix snapshots silently.
- No Cartesian explosion: generation budgets bound states/scenarios.
- Unknown/runtime-dependent states remain runtime-discovery/manual requirements.
- Every scenario must retain reason, source impact keys, evidence and confidence.
- Existing Suitest execution/test-case semantics are reused where practical, but Scenario Plans persist separately.
- Target repository remains read-only.
- One feature branch/PR: `feat/scenario-intelligence-v1`.

---

### Task 1: Scenario contracts and deterministic generator core

**Files:**
- Create: `packages/scenario-intelligence/pyproject.toml`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/__init__.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/models.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/generator.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/signature.py`
- Create: `packages/scenario-intelligence/tests/test_generator.py`
- Modify: root `pyproject.toml`

**Interfaces:**
- Consumes: `ProjectKnowledge`, `ImpactReport`, `ImpactItem`, `Confidence`, `Evidence`.
- Produces: `ScenarioPlan`, `Scenario`, `ScenarioStep`, `ScenarioPriority`, `ScenarioKind`, `AutomationReadiness`, `GenerationBudget`, `ScenarioGenerator.generate(...)`.

- [ ] Write failing tests covering fingerprint mismatch, direct route smoke, indirect route regression, state variants, unrelated-route exclusion, duplicate collapse, priority ordering and runtime-discovery behavior.
- [ ] Add workspace package/dependencies and root workspace registration.
- [ ] Implement Pydantic contracts with schema/analyzer metadata, summary counts, stable scenario keys, source impact/evidence traceability and explicit readiness.
- [ ] Implement deterministic candidate generation from direct/indirect/possible/unknown impacts and affected routes/states.
- [ ] Implement deterministic signature + merge policy preserving strongest evidence, highest priority and strictest readiness/runtime warning.
- [ ] Run focused generator tests locally during final verification.

### Task 2: Bounded state expansion, cross-state scenarios and budgets

**Files:**
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/state_expansion.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/prioritization.py`
- Extend: `packages/scenario-intelligence/src/qgate_scenario_intelligence/generator.py`
- Extend tests: `packages/scenario-intelligence/tests/test_generator.py`

**Interfaces:**
- Consumes semantic states/behavior evidence from `ProjectKnowledge` and categories from `ImpactReport`.
- Produces bounded state candidates, cross-state groups, deterministic priority/readiness decisions, coverage gaps when budgets truncate work.

- [ ] Add failing tests for auth/permission, feature flag, data-empty/present, responsive or state-pair expansion, cross-state comparison, and no Cartesian explosion.
- [ ] Implement state family/counterpart extraction conservatively from existing semantic labels/kinds/evidence; never fabricate unsupported routes or values.
- [ ] Generate `CROSS_STATE_COMPARISON` only for UI/styling/state/responsive/shared impacts with at least two related evidence-backed states.
- [ ] Implement P0–P3 deterministic scoring and readiness rules (`READY`, `RUNTIME_DISCOVERY_REQUIRED`, `MANUAL_ONLY`, `BLOCKED_BY_GAP`).
- [ ] Emit explicit coverage gaps when max scenarios/state expansions are reached.

### Task 3: Persistence, CLI and human-readable report

**Files:**
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/store.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/report.py`
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/cli.py`
- Create: `packages/scenario-intelligence/tests/test_store_cli.py`

**Interfaces:**
- Produces `JsonScenarioPlanStore` with stable key/save/load/list/latest and `qgate-scenario-intelligence generate --knowledge ... --impact ...`.

- [ ] Write failing persistence/CLI tests.
- [ ] Implement stable plan identity from project fingerprint + impact change source + deterministic scenario payload.
- [ ] Implement QGate-owned JSON persistence outside target repos.
- [ ] Implement human-readable prioritized report and `--json` output.
- [ ] Fail clearly on missing/mismatched inputs.

### Task 4: Optional bounded AI enrichment

**Files:**
- Create: `packages/scenario-intelligence/src/qgate_scenario_intelligence/semantic.py`
- Create: `packages/agent/src/suitest_agent/scenario_intelligence_semantic.py`
- Create: `packages/agent/tests/test_scenario_intelligence_semantic.py`
- Modify: `packages/agent/pyproject.toml`

**Interfaces:**
- Produces bounded `ScenarioEvidencePack` and provider-backed enrichment that can only edit human-facing wording/grouping and lower/equal priority/readiness conservatively.

- [ ] Write async tests for malformed provider fallback, unknown scenario keys ignored, no new routes/states/scenarios, no confidence increase and no runtime/manual → READY promotion.
- [ ] Build bounded packs with explicit max scenarios/evidence excerpts.
- [ ] Implement strict JSON provider prompt/response parsing using existing `LLMProvider` boundary.
- [ ] Reattach deterministic evidence and reject unsupported structural changes.
- [ ] Keep deterministic plan unchanged on provider failure.

### Task 5: Real pipeline integration fixture

**Files:**
- Create: `packages/scenario-intelligence/tests/test_frontend_integration.py`

**Interfaces:**
- Uses real `ProjectIntelligenceAnalyzer` → `LocalGitSource`/`ImpactAnalyzer` → `ScenarioGenerator` chain.

- [ ] Build temporary React/Next/TypeScript fixture with a reused component, two meaningful states, two dependent routes and one unrelated route.
- [ ] Baseline commit, modify shared UI/state behavior, generate ProjectKnowledge + ImpactReport + ScenarioPlan.
- [ ] Assert direct/indirect relevant scenarios, bounded state variants, cross-state comparison, unrelated route exclusion, dedupe, evidence traceability and persistence round-trip.
- [ ] Add runtime-only/unknown coverage case.

### Task 6: Local read-only API

**Files:**
- Create: `apps/api/src/suitest_api/routers/scenario_intelligence.py`
- Modify: `apps/api/src/suitest_api/routers/projects.py`
- Modify: `apps/api/src/suitest_api/settings.py`
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/tests/test_scenario_intelligence_api.py`
- Modify: `.env.example`

**Interfaces:**
- Endpoints: `GET /api/v1/scenario-intelligence/plans`, `/latest`, `/plans/{key}`.

- [ ] Write tests for authenticated local list/latest/detail, empty latest 404 and server-mode hidden 404.
- [ ] Add `SUITEST_SCENARIO_INTELLIGENCE_DIR` setting defaulting to `~/.qgate/scenario-intelligence`.
- [ ] Implement read-only router using persisted plans only; no filesystem path input.
- [ ] Register router with minimal existing-pattern changes.

### Task 7: `/scenarios` dashboard

**Files:**
- Create: `apps/web/src/hooks/use-scenario-intelligence.ts`
- Create: `apps/web/src/routes/_app/scenarios.tsx`
- Create: `apps/web/src/routes/_app/scenarios.test.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Generated during local verification: `apps/web/src/routeTree.gen.ts`

**Interfaces:**
- Reads latest ScenarioPlan API and renders priority/readiness, target route/state, steps, rationale/evidence, cross-state group and coverage gaps.

- [ ] Write web tests for populated and empty plan states.
- [ ] Implement query hook following Project Map/Impact patterns.
- [ ] Implement `/scenarios` route with concise prioritized list and readiness/runtime warnings.
- [ ] Add Insights sidebar entry.
- [ ] Regenerate TanStack route tree through repository tooling during Antigravity verification.

### Task 8: Documentation, lockfile and full verification handoff

**Files:**
- Create: `docs/SCENARIO_INTELLIGENCE.md`
- Modify: `docs/API.md`
- Review/update if needed: `docs/README.md`, `.env.example`
- Generated during local verification: `uv.lock`
- Do NOT mark Phase 3 complete in `QGATE_PROGRESS.md` until PR is merged.

- [ ] Document architecture, workflow, contracts, readiness, AI guardrails, limitations and execution handoff.
- [ ] Document local read-only API endpoints.
- [ ] Verify docs index already references Scenario Intelligence; change only if needed.
- [ ] Antigravity runs `uv lock`, route generation, unit/integration/API/web suites, Ruff, mypy, web typecheck/build, CLI smokes and visual `/scenarios` smoke.
- [ ] Fix only genuine issues on the same branch and rerun affected checks.
- [ ] After verification PASS, open one PR `feat: Scenario Intelligence V1`; do not merge until explicit approval/workflow handoff.
