# Browser Execution & Evidence V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute eligible Scenario Intelligence outputs in a real browser through the existing Suitest/Playwright foundation and persist structured, redacted evidence without confusing application assertion failures with setup/environment failures.

**Architecture:** Add a focused QGate browser-execution package that compiles `ScenarioPlan` entries into a small deterministic browser operation vocabulary, delegates browser provisioning/runtime to existing Suitest lifecycle/Playwright primitives, captures bounded evidence, and persists an `ExecutionReport` projection. Keep runtime resolution, evidence collection, failure classification, persistence, CLI/API/dashboard concerns separated so later Final Gate can consume stable facts.

**Tech Stack:** Python 3.12, Pydantic v2, existing `qgate-scenario-intelligence`, existing `suiflex-suitest-lifecycle` Playwright/runtime/blackbox selector primitives, FastAPI, React 19 + TanStack Router + TypeScript, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-browser-execution-evidence-v1-design.md`

## Global Constraints

- Reuse Suitest/Playwright execution/runtime primitives; do not build a second generic browser engine.
- Only `READY` scenarios auto-run by default; readiness is never silently upgraded.
- Assertion failure is not final product-bug judgement.
- Environment/setup/browser/target-resolution/test-definition failures remain distinct.
- No arbitrary JavaScript generated from Scenario Intelligence.
- Robust semantic target resolution only; no random brittle selector guessing.
- Evidence must be bounded and redact secrets/auth/payment-sensitive values.
- Target repository remains read-only.
- One feature branch/PR: `feat/browser-execution-evidence-v1`.

---

### Task 1: Execution contracts and deterministic compiler

**Files:**
- Create: `packages/browser-execution/pyproject.toml`
- Create: `packages/browser-execution/src/qgate_browser_execution/__init__.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/models.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/compiler.py`
- Create: `packages/browser-execution/tests/test_compiler.py`
- Modify: root `pyproject.toml`

**Interfaces:**
- Consumes: `ScenarioPlan`, `Scenario`, `ScenarioStep`, `AutomationReadiness`.
- Produces: `OperationKind`, `ExecutionRequest`, `CompiledScenario`, `CompiledStep`, `ExecutionStatus`, `FailureCategory`, `ExecutionConfig`, `ScenarioCompiler.compile_plan(...)`.

- [ ] **Step 1: Write failing compiler tests**

```python
def test_ready_route_scenario_compiles_to_navigate_and_capture() -> None:
    request = ScenarioCompiler().compile_plan(plan, ExecutionConfig(base_url="http://127.0.0.1:4173"))
    assert request.scenarios[0].steps[0].operation == OperationKind.NAVIGATE


def test_runtime_discovery_is_not_promoted_to_ready() -> None:
    request = ScenarioCompiler().compile_plan(runtime_plan, ExecutionConfig(base_url="http://127.0.0.1:4173"))
    assert request.unverified[0].status == ExecutionStatus.UNVERIFIED
```

- [ ] **Step 2: Run focused tests and confirm they fail before implementation**

Run: `uv run pytest packages/browser-execution/tests/test_compiler.py -q`
Expected: import/module failures.

- [ ] **Step 3: Implement Pydantic execution contracts and small operation vocabulary**

```python
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
```

- [ ] **Step 4: Implement deterministic compilation policy**

```python
if scenario.readiness is not AutomationReadiness.READY:
    return preclassified_unverified(scenario)
if not scenario.routes:
    return unsupported("ready scenario has no executable route")
```

Map existing route-oriented Scenario steps conservatively. Unsupported ambiguous actions stay unverified/test-definition-error; do not invent selectors/credentials/values.

- [ ] **Step 5: Run compiler tests and commit**

Run: `uv run pytest packages/browser-execution/tests/test_compiler.py -q`
Expected: PASS.

### Task 2: Runtime resolver and bounded evidence/redaction

**Files:**
- Create: `packages/browser-execution/src/qgate_browser_execution/resolver.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/evidence.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/redaction.py`
- Create: `packages/browser-execution/tests/test_evidence.py`

**Interfaces:**
- Reuses: `suitest_lifecycle.blackbox.models.ElementInfo`, `suitest_lifecycle.blackbox.selector.describe/build_locator` where safe.
- Produces: `TargetDescriptor`, `EvidenceRecord`, `ConsoleEvidence`, `NetworkEvidence`, `DomEvidence`, redaction helpers.

- [ ] **Step 1: Add failing tests for locator ambiguity and redaction**

```python
def test_multiple_semantic_matches_are_not_randomly_selected() -> None:
    result = resolve_target([button_a, button_b], TargetHint(role="button", name="Save"))
    assert result.resolved is False
    assert result.failure_category == FailureCategory.TARGET_RESOLUTION_FAILURE


def test_sensitive_headers_are_redacted() -> None:
    assert redact_headers({"Authorization": "Bearer secret"})["Authorization"] == "<redacted>"
```

- [ ] **Step 2: Implement semantic target priority**

Use trusted explicit metadata, role/name, label, existing test id, safe visible text, then already-supplied verified selector. Never select ambiguous candidates randomly.

- [ ] **Step 3: Implement bounded evidence models**

Capture only relevant element text/value/state, bounded DOM excerpt, selected computed CSS keys, console errors/warnings, redacted network metadata and artifact references.

- [ ] **Step 4: Implement redaction rules**

Redact authorization/cookie headers, password/token/secret/payment-like fields and configured secret values before persistence.

- [ ] **Step 5: Run evidence tests and commit**

Run: `uv run pytest packages/browser-execution/tests/test_evidence.py -q`
Expected: PASS.

### Task 3: Playwright execution adapter and classification

**Files:**
- Create: `packages/browser-execution/src/qgate_browser_execution/executor.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/classification.py`
- Create: `packages/browser-execution/tests/test_executor_unit.py`

**Interfaces:**
- Consumes: `ExecutionRequest`.
- Reuses: `suitest_lifecycle.frontend_runtime.ensure_browser` and Playwright async runtime.
- Produces: `ExecutionReport`, `ScenarioExecution`, `StepExecution`.

- [ ] **Step 1: Add failing unit tests using a fake page/runtime**

```python
async def test_assertion_mismatch_is_failed_assertion_not_environment_error() -> None:
    report = await executor.run(request, runtime=fake_runtime(actual_text="Total"))
    assert report.scenarios[0].status == ExecutionStatus.FAILED
    assert report.scenarios[0].failure_category == FailureCategory.ASSERTION_FAILURE


async def test_browser_start_failure_is_execution_error() -> None:
    report = await executor.run(request, runtime=failing_runtime())
    assert report.scenarios[0].status == ExecutionStatus.EXECUTION_ERROR
    assert report.scenarios[0].failure_category == FailureCategory.BROWSER_FAILURE
```

- [ ] **Step 2: Implement browser readiness and async runtime adapter**

Call existing `ensure_browser`; use Chromium through Playwright async API. Keep one browser context per plan run unless scenario isolation requires a new context.

- [ ] **Step 3: Implement supported operations**

Implement NAVIGATE, CAPTURE, semantic CLICK/FILL/SELECT where trusted target metadata is present, and deterministic visible/text/value/url/attribute/layout assertions. Unsupported operation returns explicit test-definition/unverified result.

- [ ] **Step 4: Capture step evidence**

Collect final URL, relevant DOM/target snapshot, selected computed CSS, console/network events during the scenario window, screenshot on failures/checkpoints, timings and artifact paths.

- [ ] **Step 5: Implement conservative retry**

No retry for deterministic assertion failure; at most one configured retry for transient browser/navigation/infrastructure failure; retain attempt history.

- [ ] **Step 6: Run executor unit tests and commit**

Run: `uv run pytest packages/browser-execution/tests/test_executor_unit.py -q`
Expected: PASS.

### Task 4: Real browser integration fixtures

**Files:**
- Create: `packages/browser-execution/tests/fixtures/browser_app.html`
- Create: `packages/browser-execution/tests/test_browser_integration.py`

**Interfaces:**
- Uses a temporary local HTTP server + real Playwright Chromium.

- [ ] **Step 1: Build fixture with deterministic pass/fail states**

Fixture must expose: `/`-equivalent page content, semantic buttons/text, one expected label that can intentionally mismatch, console event, and a lightweight fetch endpoint or mocked network failure.

- [ ] **Step 2: Verify a passing READY scenario**

```python
assert scenario_run.status == ExecutionStatus.PASSED
assert scenario_run.verified is True
assert scenario_run.evidence
```

- [ ] **Step 3: Verify deliberate application regression**

Expected text `You Pay`, actual text `Total` must produce `FAILED + ASSERTION_FAILURE` with screenshot/DOM evidence.

- [ ] **Step 4: Verify unavailable target/server**

A dead base URL must produce `EXECUTION_ERROR` with navigation/environment category, never `ASSERTION_FAILURE`.

- [ ] **Step 5: Verify manual/runtime-discovery scenarios remain unverified/skipped**

- [ ] **Step 6: Run real browser integration and commit**

Run: `uv run pytest packages/browser-execution/tests/test_browser_integration.py -q`
Expected: PASS with Chromium available/provisioned by existing lifecycle support.

### Task 5: Persistence, CLI and report rendering

**Files:**
- Create: `packages/browser-execution/src/qgate_browser_execution/store.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/report.py`
- Create: `packages/browser-execution/src/qgate_browser_execution/cli.py`
- Create: `packages/browser-execution/tests/test_store_cli.py`

**Interfaces:**
- Produces `JsonExecutionReportStore`, stable run key, `qgate-browser-execution run`.

- [ ] **Step 1: Add failing store/CLI tests**

```python
path = store.save(report)
assert store.load_key(store.key_for(report)) == report
```

- [ ] **Step 2: Implement stable QGate report persistence**

Identity includes ScenarioPlan key/project fingerprint/execution configuration fingerprint/run id. Large screenshots/video/trace stay referenced as artifacts, not embedded.

- [ ] **Step 3: Implement CLI**

Support plan path, base URL, optional scenario/priority filters, `--json`, store dir, safe timeout/retry bounds; default ready-only execution.

- [ ] **Step 4: Human-readable report output**

Show executed/passed/failed/error/unverified/manual counts and per-scenario reason/evidence refs.

- [ ] **Step 5: Run store/CLI tests and commit**

### Task 6: Local read-only API and settings

**Files:**
- Create: `apps/api/src/suitest_api/routers/browser_execution.py`
- Create: `apps/api/tests/test_browser_execution_api.py`
- Modify: `apps/api/src/suitest_api/routers/projects.py`
- Modify: `apps/api/src/suitest_api/settings.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `.env.example`

**Interfaces:**
- `GET /api/v1/browser-execution/reports`
- `GET /api/v1/browser-execution/latest`
- `GET /api/v1/browser-execution/reports/{key}`

- [ ] **Step 1: Add failing authenticated local/server-mode API tests**
- [ ] **Step 2: Add `SUITEST_BROWSER_EXECUTION_DIR=~/.qgate/browser-execution` setting**
- [ ] **Step 3: Implement read-only local router using persisted reports only**
- [ ] **Step 4: Register router/dependency minimally**
- [ ] **Step 5: Run API tests and commit**

### Task 7: Execution dashboard

**Files:**
- Create: `apps/web/src/hooks/use-browser-execution.ts`
- Create: `apps/web/src/routes/_app/execution.tsx`
- Create: `apps/web/src/routes/_app/execution.test.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Generated during local verification: `apps/web/src/routeTree.gen.ts`

**Interfaces:**
- Reads latest ExecutionReport and renders plan-vs-run coverage, statuses, failure categories and evidence refs.

- [ ] **Step 1: Add populated + empty-state web tests**
- [ ] **Step 2: Implement query hook**
- [ ] **Step 3: Implement `/execution` dashboard**

Show scenario status, verification flag, failure category, route, timings, step results, console/network summary, screenshots/artifact refs, retries, gaps.

- [ ] **Step 4: Add Insights sidebar entry**
- [ ] **Step 5: Regenerate route tree in Antigravity verification**

### Task 8: Documentation and final verification handoff

**Files:**
- Create: `docs/BROWSER_EXECUTION_EVIDENCE.md`
- Modify: `docs/API.md`
- Review/update if needed: `docs/README.md`, `.env.example`
- Generated during verification: `uv.lock`
- Do NOT mark Phase 4 complete in `QGATE_PROGRESS.md` before merge.

- [ ] **Step 1: Document execution contracts, classification boundary, evidence/redaction, retries and limitations**
- [ ] **Step 2: Document local read-only API endpoints**
- [ ] **Step 3: Run Antigravity full local verification**

Verification must cover package tests, real Chromium fixture, deliberate assertion regression, dead-server/environment failure, redaction, readiness preservation, CLI, API, web, Ruff, mypy, route generation, uv lock, web typecheck/build and affected suites.

- [ ] **Step 4: Fix only genuine issues on the same branch and rerun affected checks**
- [ ] **Step 5: After verification PASS, open one PR `feat: Browser Execution & Evidence V1`; do not merge until workflow handoff/approval.**
