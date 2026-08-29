# State-Aware Execution + Suitest Sync V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make QGate stateful scenarios establish their required browser state instead of passing on route-only evidence, and project executable QGate scenarios into visible, idempotent Suitest test cases.

**Architecture:** Keep ScenarioPlan/ExecutionReport as canonical QGate artifacts. Add an explicit bounded runtime state setup hint to Scenario Intelligence, consume it in Browser Execution before scenario assertions, and fail closed when a required state cannot be established. Add an API-side materializer that reuses existing Suitest TestCaseService semantics to create/update QGate-managed cases in a caller-selected Suitest suite.

**Tech Stack:** Python, Pydantic, FastAPI, SQLAlchemy, existing QGate Scenario Intelligence and Browser Execution packages, existing Suitest TestCaseService/repositories.

**Spec:** `docs/superpowers/specs/2026-08-29-state-aware-suitest-sync-v1-design.md`

## Global Constraints

- No wallet-, fixture-, route-, or project-specific production hard-coding.
- Required state unresolved or unverifiable must not PASS.
- Reuse existing CLICK/NAVIGATE/assertion operations where possible.
- QGate artifacts remain canonical; Suitest cases are a user-visible synchronized projection.
- Materialization must be idempotent for exact scenario identity.
- Do not alter Final Gate decision policy, local auth bypass, or LLM configuration behavior.
- Do not modify the target application.

---

### Task 1: Add explicit bounded runtime state setup hints to Scenario Intelligence

**Files:**
- Modify: `packages/scenario-intelligence/src/qgate_scenario_intelligence/models.py`
- Modify: `packages/scenario-intelligence/src/qgate_scenario_intelligence/generator.py`
- Test: `packages/scenario-intelligence/tests/test_generator.py`

**Interfaces:**
- Produces: `StateSetupHint` attached to `Scenario.state_setup_hints`.
- Consumes: existing `SemanticState` label/kind/confidence/evidence.

- [ ] **Step 1: Write failing generator tests** proving that a high/medium-confidence evidence-backed UI-reachable semantic state receives a bounded UI-control setup hint, while unknown/runtime-only states remain without a deterministic hint.
- [ ] **Step 2: Add `StateSetupMechanism` and `StateSetupHint` models** with semantic state key/label, mechanism, target label, optional value, verification text/attribute, confidence and evidence.
- [ ] **Step 3: Populate state setup hints conservatively** for evidence-backed user/feature/data states where the semantic label can be used as an obvious accessible UI control label. Do not promote technical/runtime states or low-confidence ambiguous states.
- [ ] **Step 4: Keep readiness fail-closed**: a state scenario may be READY only when its route is known and at least one deterministic setup hint exists; otherwise it remains runtime discovery required.
- [ ] **Step 5: Run Scenario Intelligence tests.**

### Task 2: Compile required state setup before assertions and fail closed on missing setup

**Files:**
- Modify: `packages/browser-execution/src/qgate_browser_execution/models.py`
- Modify: `packages/browser-execution/src/qgate_browser_execution/compiler.py`
- Modify: `packages/browser-execution/src/qgate_browser_execution/executor.py`
- Test: `packages/browser-execution/tests/test_compiler.py`
- Test: `packages/browser-execution/tests/test_executor.py`

**Interfaces:**
- Consumes: `Scenario.state_setup_hints`.
- Produces: setup CLICK plus verification step(s) before scenario actions, with setup failures classified as `STATE_SETUP_FAILURE`.

- [ ] **Step 1: Write failing compiler tests** for a state scenario that must compile as NAVIGATE -> state CLICK -> state verification -> scenario action/assertion/capture.
- [ ] **Step 2: Add a `state_setup` marker on `CompiledStep`** so executor/classifier can distinguish setup failures from product assertion failures without inventing a new execution engine.
- [ ] **Step 3: Extend `ScenarioCompiler`** to consume the bounded UI-control hint, emit CLICK using accessible label/name text, then emit a verification step proving the selected state control is active/visible. Preserve existing scenario steps afterward.
- [ ] **Step 4: Prevent route-only false verification**: any scenario with semantic states but no usable setup hint becomes `UNVERIFIED` instead of NAVIGATE+CAPTURE.
- [ ] **Step 5: Classify failures on setup-marked steps as `STATE_SETUP_FAILURE`** while keeping scenario assertions as `ASSERTION_FAILURE`.
- [ ] **Step 6: Run Browser Execution tests.**

### Task 3: Materialize executable QGate scenarios into visible Suitest test cases

**Files:**
- Create: `apps/api/src/suitest_api/services/qgate_test_materializer.py`
- Modify: `apps/api/src/suitest_api/routers/scenario_intelligence.py`
- Test: `apps/api/tests/test_qgate_test_materializer.py`
- Test: `apps/api/tests/test_scenario_intelligence.py`

**Interfaces:**
- New API: `POST /api/v1/scenario-intelligence/plans/{key}/materialize` with `suiteId`.
- Produces: a response listing created/updated/skipped Suitest case ids/public ids for that plan.
- Reuses: `TestCaseService.create`, `TestCaseService.update`, `TestCaseService.replace_steps`, `TestCaseRepo`, `SuiteRepo`, `ProjectRepo`.

- [ ] **Step 1: Write failing materializer tests** for create, exact-identity reuse/update, unresolved scenario skip, and distinct change identity isolation.
- [ ] **Step 2: Implement QGate identity tags** using bounded tag values: `qgate-managed`, `qgate-scenario:<key>`, `qgate-change:<change-id>`, `qgate-project:<fingerprint>`.
- [ ] **Step 3: Convert executable QGate scenario steps to existing Suitest `StepCreate`** using natural action/expected text and `mcpProvider="playwright"`/`targetKind=FE_WEB`, preserving compiled order where available.
- [ ] **Step 4: Reuse exact identity** by finding an existing case in the selected suite with the exact `qgate-scenario:<key>` plus current change/project tags. Update metadata/steps instead of creating a duplicate.
- [ ] **Step 5: Add the materialize endpoint** guarded by existing workspace membership/writer role and local-mode ScenarioPlan store. Return explicit created/updated/skipped outcomes; never fabricate execution evidence.
- [ ] **Step 6: Confirm the materialized cases are visible through the existing Test Cases list/read API.**
- [ ] **Step 7: Run API/test-case regression tests.**

### Task 4: Reconcile stateful evidence with current Final Gate contract

**Files:**
- Test: `packages/final-gate/tests/test_judge.py`
- Test: integration/fixture test location chosen from existing QGate validation tests.

**Interfaces:**
- Consumes: current `ExecutionReport`; no Final Gate policy API change.

- [ ] **Step 1: Add a regression test** showing a required state scenario with setup failure is not eligible for PASS.
- [ ] **Step 2: Add a regression test** showing a pipeline-owned verified assertion failure in the stateful scenario yields `BLOCK`.
- [ ] **Step 3: Do not alter Final Gate logic unless a failing regression test proves an actual policy bug.**

### Task 5: Documentation and end-to-end validation handoff

**Files:**
- Modify: `docs/BROWSER_EXECUTION.md` if present, otherwise the existing Browser Execution documentation file.
- Modify: `docs/SCENARIO_INTELLIGENCE.md` if present.
- Modify: `docs/API.md` for the materialize endpoint.

- [ ] **Step 1: Document state setup/fail-closed semantics.**
- [ ] **Step 2: Document QGate-managed Suitest tags and idempotency.**
- [ ] **Step 3: Document the materialize endpoint and that QGate JSON artifacts remain canonical.**
- [ ] **Step 4: Local verification must rerun the existing unchanged wallet fixture** from baseline `1ed1d06f01681a69ffbd5388771da512c61affd6` to buggy `40cf5de975eb6b0c8779a163acebf44b92fa885d`.
- [ ] **Step 5: Required validation outcome:** state is established by pipeline-owned steps; if the existing QGate assertions expose the wrong final payable, the current scenario must produce verified failure and Final Gate `BLOCK`; otherwise report the remaining assertion-generation gap rather than forcing BLOCK.
- [ ] **Step 6: Confirm at least one QGate-managed generated case is visible in the Suitest Tests UI and repeated materialization does not duplicate it.
