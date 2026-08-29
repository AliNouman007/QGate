# Final Gate V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build QGate Final Gate V1, a strict deterministic decision layer that consumes the merged QGate evidence chain and returns `PASS`, `BLOCK`, or `MANUAL_REVIEW_REQUIRED` with inspectable evidence and decision trace.

**Architecture:** Add a focused `qgate-final-gate` Python package that validates artifact identity, evaluates importance-aware coverage, classifies verified blockers vs manual-review gaps, consumes already-ranked QA Memory recall, and emits a persisted `GateReport`. Optional AI may only explain deterministic results. Expose reports through local CLI/API/dashboard using existing QGate patterns.

**Tech Stack:** Python 3.12, Pydantic v2, existing QGate packages (`project-intelligence`, `impact-analysis`, `scenario-intelligence`, `browser-execution`, `qa-memory`), FastAPI, React 19, TanStack Router/Query, TypeScript, pytest, Vitest, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-08-29-final-gate-v1-design.md`

## Global Constraints

- Public verdict enum is exactly `PASS`, `BLOCK`, `MANUAL_REVIEW_REQUIRED`.
- Deterministic engine owns the verdict; AI cannot improve a verdict to PASS or downgrade a verified blocker.
- Input identity/fingerprint/change-source mismatches fail closed to manual review, never product BLOCK by themselves.
- P0/P1 are required; P2 is required only when directly impacted or strongly backed by active historical regression risk; P3 is optional unless explicitly promoted.
- Zero meaningful required coverage cannot silently PASS.
- Browser environment/setup/target/test-definition failures are not product bugs.
- Historical QA Memory is risk/provenance, never current defect proof.
- Reuse existing Browser Execution classification and QA Memory recall; do not build duplicate classifiers/relevance engines.
- QGate data persists outside target repositories.
- V1 detects/reports only; no production code fixes, PR merges, or human-approval bypass.
- `QGATE_PROGRESS.md` is not marked complete until the feature is merged and locally verified.

---

## File Structure

Create package `packages/final-gate/`:

- `models.py` — public Gate contracts/enums.
- `integrity.py` — artifact chain validation.
- `coverage.py` — required-scenario policy and CoverageItem construction.
- `judge.py` — deterministic verdict precedence and findings.
- `memory.py` — historical regression obligation mapping from `MemoryRecallResult` only.
- `ai.py` — bounded optional explanation contract/provider wrapper.
- `store.py` — JSON GateReport persistence.
- `report.py` — human-readable rendering.
- `cli.py` — local Final Gate command.

Integrations:

- `apps/api/src/suitest_api/routers/final_gate.py`
- `apps/web/src/hooks/use-final-gate.ts`
- `apps/web/src/routes/_app/gate.tsx`
- `apps/web/src/routes/_app/gate.test.tsx`
- root/API package `pyproject.toml`, `.env.example`, router/sidebar/routeTree wiring, docs.

---

### Task 1: Gate contracts and input-integrity validation

**Files:**
- Create: `packages/final-gate/pyproject.toml`
- Create: `packages/final-gate/src/qgate_final_gate/__init__.py`
- Create: `packages/final-gate/src/qgate_final_gate/models.py`
- Create: `packages/final-gate/src/qgate_final_gate/integrity.py`
- Test: `packages/final-gate/tests/test_integrity.py`

**Interfaces:**
- Consumes: `ProjectKnowledge`, `ImpactReport`, `ScenarioPlan`, `ExecutionReport`, optional `MemoryRecallResult`.
- Produces: `GateInputBundle`, `InputIntegrityFinding`, `GateReasonKind`, `validate_input_integrity(bundle) -> list[InputIntegrityFinding]`.

- [ ] **Step 1: Write failing integrity tests**

```python

def test_matching_chain_has_no_integrity_findings(bundle: GateInputBundle) -> None:
    assert validate_input_integrity(bundle) == []


def test_project_fingerprint_mismatch_is_manual_gap(bundle: GateInputBundle) -> None:
    bundle.execution.metadata.project_fingerprint = "stale"
    findings = validate_input_integrity(bundle)
    assert findings[0].kind == GateReasonKind.INPUT_INTEGRITY_GAP
    assert findings[0].verdict_effect == VerdictEffect.MANUAL_REVIEW


def test_execution_plan_key_mismatch_is_manual_gap(bundle: GateInputBundle) -> None:
    bundle.execution.metadata.scenario_plan_key = "wrong"
    assert any("scenario plan" in f.reason.lower() for f in validate_input_integrity(bundle))
```

- [ ] **Step 2: Run integrity tests and confirm RED**

Run: `uv run pytest packages/final-gate/tests/test_integrity.py -q`
Expected: FAIL because `qgate_final_gate` contracts/functions do not exist.

- [ ] **Step 3: Implement minimal contracts**

```python
class GateVerdict(StrEnum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

class VerdictEffect(StrEnum):
    BLOCKING = "blocking"
    MANUAL_REVIEW = "manual_review"
    INFORMATIONAL = "informational"

class GateReasonKind(StrEnum):
    VERIFIED_PRODUCT_FAILURE = "verified_product_failure"
    REQUIRED_SCENARIO_UNVERIFIED = "required_scenario_unverified"
    REQUIRED_SCENARIO_BLOCKED = "required_scenario_blocked"
    REQUIRED_SCENARIO_MANUAL_ONLY = "required_scenario_manual_only"
    ENVIRONMENT_OR_SETUP_GAP = "environment_or_setup_gap"
    TARGET_RESOLUTION_GAP = "target_resolution_gap"
    TEST_DEFINITION_GAP = "test_definition_gap"
    TIMEOUT_UNRESOLVED = "timeout_unresolved"
    HISTORICAL_REGRESSION_UNVERIFIED = "historical_regression_unverified"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    INPUT_INTEGRITY_GAP = "input_integrity_gap"
    COVERAGE_TRUNCATED = "coverage_truncated"
    NO_REQUIRED_COVERAGE = "no_required_coverage"
    ALL_REQUIRED_COVERAGE_VERIFIED = "all_required_coverage_verified"
```

Add `CoverageOutcome`, `GateConfidence`, `GateFinding`, `CoverageItem`, `CoverageSummary`, `DecisionTraceEntry`, `HistoricalRisk`, `GateMetadata`, `GateReport`, and `GateInputBundle` using explicit Pydantic fields from the spec.

- [ ] **Step 4: Implement identity validation**

Validate:

```python
project.metadata.source_id == impact.metadata.project_source_id
project.metadata.source_fingerprint == impact.metadata.project_fingerprint
scenario.metadata.project_source_id == impact.metadata.project_source_id
scenario.metadata.project_fingerprint == impact.metadata.project_fingerprint
scenario.metadata.impact_change_source_id == impact.metadata.change_source_id
execution.metadata.project_source_id == scenario.metadata.project_source_id
execution.metadata.project_fingerprint == scenario.metadata.project_fingerprint
execution.metadata.impact_change_source_id == scenario.metadata.impact_change_source_id
execution.metadata.scenario_plan_key == scenario_plan_key
```

When memory exists also validate `project_source_id`, `project_fingerprint`, `impact_change_source_id`.

- [ ] **Step 5: Run tests GREEN**

Run: `uv run pytest packages/final-gate/tests/test_integrity.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/final-gate
git commit -m "feat(final-gate): add contracts and input integrity"
```

---

### Task 2: Importance-aware coverage and historical regression obligations

**Files:**
- Create: `packages/final-gate/src/qgate_final_gate/coverage.py`
- Create: `packages/final-gate/src/qgate_final_gate/memory.py`
- Test: `packages/final-gate/tests/test_coverage.py`
- Test: `packages/final-gate/tests/test_memory_obligations.py`

**Interfaces:**
- Consumes: `ScenarioPlan`, `ExecutionReport`, `ImpactReport`, optional `MemoryRecallResult`.
- Produces: `build_coverage(...) -> tuple[list[CoverageItem], CoverageSummary]`, `build_historical_risks(...) -> list[HistoricalRisk]`.

- [ ] **Step 1: Write failing required-policy tests**

```python

def test_p0_and_p1_are_required(plan, execution, impact):
    items, _ = build_coverage(plan, execution, impact, None)
    required = {i.scenario_key for i in items if i.required}
    assert {"p0", "p1"} <= required


def test_direct_p2_is_required(plan, execution, impact):
    item = next(i for i in build_coverage(plan, execution, impact, None)[0] if i.scenario_key == "p2_direct")
    assert item.required is True
    assert "direct impact" in item.required_reason.lower()


def test_optional_p3_environment_failure_does_not_create_required_gap(...):
    item = ...
    assert item.required is False
    assert item.coverage_outcome == CoverageOutcome.OPTIONAL
```

- [ ] **Step 2: Write failing historical-memory tests**

Use real `MemoryRecallResult.matched_rules` shape from QA Memory.

```python

def test_strong_recalled_rule_promotes_related_scenario_to_required(...):
    items, _ = build_coverage(plan, execution, impact, recall)
    wallet = next(i for i in items if i.scenario_key == "checkout_wallet")
    assert wallet.required is True
    assert wallet.historical_regression_linkage


def test_strong_recall_without_matching_scenario_creates_unverified_historical_risk(...):
    risks = build_historical_risks(plan, execution, impact, recall)
    assert risks[0].covered is False
```

- [ ] **Step 3: Run coverage tests RED**

Run: `uv run pytest packages/final-gate/tests/test_coverage.py packages/final-gate/tests/test_memory_obligations.py -q`
Expected: FAIL.

- [ ] **Step 4: Implement deterministic required-policy**

Rules:

```python
P0 -> required
P1 -> required
P2 + DIRECT impact/source_impact_key match -> required
P2 + strong active recalled regression relation -> required
P3 -> optional unless explicitly promoted by strong regression relation
```

Do not invent new scenarios. Map scenario executions by `scenario_key`; absent required execution yields `UNVERIFIED`.

- [ ] **Step 5: Map execution states to coverage outcomes**

```python
PASSED + verified -> VERIFIED_PASS
FAILED + verified -> VERIFIED_FAIL
SKIPPED_MANUAL -> MANUAL
BLOCKED -> BLOCKED
anything else -> UNVERIFIED
```

Preserve `failure_category` and evidence refs.

- [ ] **Step 6: Implement historical obligation logic from recall only**

Use recalled rule score/reasons and current impact relation; do not re-rank the whole memory store. Strongly related rule with no verified corresponding scenario creates `HistoricalRisk(covered=False)`.

- [ ] **Step 7: Run tests GREEN**

Run: `uv run pytest packages/final-gate/tests/test_coverage.py packages/final-gate/tests/test_memory_obligations.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/final-gate/src/qgate_final_gate/coverage.py packages/final-gate/src/qgate_final_gate/memory.py packages/final-gate/tests
git commit -m "feat(final-gate): evaluate required coverage and historical risk"
```

---

### Task 3: Deterministic verdict judge and decision trace

**Files:**
- Create: `packages/final-gate/src/qgate_final_gate/judge.py`
- Create: `packages/final-gate/src/qgate_final_gate/report.py`
- Test: `packages/final-gate/tests/test_judge.py`
- Test: `packages/final-gate/tests/test_end_to_end_gate.py`

**Interfaces:**
- Consumes: `GateInputBundle`.
- Produces: `FinalGateJudge.evaluate(bundle) -> GateReport`, `render_gate_report(report) -> str`.

- [ ] **Step 1: Write failing BLOCK/MANUAL/PASS precedence tests**

```python

def test_verified_required_assertion_failure_blocks(bundle):
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.BLOCK
    assert report.blocking_findings[0].kind == GateReasonKind.VERIFIED_PRODUCT_FAILURE


def test_required_environment_failure_is_manual_not_block(bundle):
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert not report.blocking_findings


def test_all_required_verified_pass_returns_pass(bundle):
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.PASS
    assert report.confidence == GateConfidence.HIGH


def test_zero_required_coverage_is_manual(bundle):
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert any(f.kind == GateReasonKind.NO_REQUIRED_COVERAGE for f in report.manual_review_findings)
```

- [ ] **Step 2: Add timeout/conflict/truncation tests**

Cover:
- required timeout => MANUAL unless independent verified product assertion already establishes failure;
- scenario or execution gap affecting required P0/P1 => MANUAL;
- ScenarioPlan budget/truncation affecting potentially required work => MANUAL;
- verified product blocker takes precedence over simultaneous manual gaps;
- input mismatch => MANUAL unless independent current verified blocker exists in an otherwise invalid chain; invalid chain must prevent trusting that blocker, therefore MANUAL.

- [ ] **Step 3: Run judge tests RED**

Run: `uv run pytest packages/final-gate/tests/test_judge.py packages/final-gate/tests/test_end_to_end_gate.py -q`
Expected: FAIL.

- [ ] **Step 4: Implement deterministic judge in ordered stages**

```python
integrity = validate_input_integrity(bundle)
if integrity:
    return manual_report(...)
coverage, summary = build_coverage(...)
historical = build_historical_risks(...)
blocking = collect_verified_product_failures(coverage, bundle.execution)
manual = collect_required_gaps(coverage, historical, bundle.scenario, bundle.execution)
if blocking:
    verdict = BLOCK
elif manual:
    verdict = MANUAL_REVIEW_REQUIRED
elif summary.required_total == 0:
    verdict = MANUAL_REVIEW_REQUIRED
else:
    verdict = PASS
```

BLOCK qualification must require relevant scenario, `verified=True`, product/application evidence, and allowed product-failure category (primarily assertion failure). Environment/setup categories never directly block.

- [ ] **Step 5: Build ordered `decision_trace`**

Every fired rule gets a stable rule id, human-readable reason, and source references. AI is not used here.

- [ ] **Step 6: Add human-readable renderer**

First line examples:

```text
BLOCK — checkout_wallet violated expected invariant "You Pay" (verified assertion failure)
MANUAL REVIEW REQUIRED — P1 checkout_wallet was not verified because state setup failed
PASS — all 4 required scenarios verified with no blocking product failures
```

- [ ] **Step 7: Run judge tests GREEN**

Run: `uv run pytest packages/final-gate/tests/test_judge.py packages/final-gate/tests/test_end_to_end_gate.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/final-gate
git commit -m "feat(final-gate): add deterministic verdict judge"
```

---

### Task 4: Bounded AI explanation, persistence, and CLI

**Files:**
- Create: `packages/final-gate/src/qgate_final_gate/ai.py`
- Create: `packages/final-gate/src/qgate_final_gate/store.py`
- Create: `packages/final-gate/src/qgate_final_gate/cli.py`
- Test: `packages/final-gate/tests/test_ai.py`
- Test: `packages/final-gate/tests/test_store.py`
- Test: `packages/final-gate/tests/test_cli.py`

**Interfaces:**
- Consumes: deterministic `GateReport` plus bounded evidence excerpts.
- Produces: optional `GateAIExplanation`; persisted/reloaded `GateReport`; CLI command `qgate-final-gate`.

- [ ] **Step 1: Write failing AI guardrail tests**

```python

def test_ai_cannot_change_verdict(block_report, fake_provider):
    fake_provider.response = {"verdict": "PASS", "summary": "looks good"}
    enriched = explain_gate(block_report, fake_provider)
    assert enriched.verdict == GateVerdict.BLOCK
    assert enriched.ai_explanation.summary == "looks good"


def test_invalid_ai_response_falls_back_to_deterministic_report(...):
    ...
```

- [ ] **Step 2: Implement bounded `GateEvidencePack`**

Include only verdict, fired rule ids, bounded findings, bounded coverage, bounded historical risks, bounded evidence excerpts/refs. Never whole repo/log/history.

- [ ] **Step 3: Write store traversal/round-trip tests and implement `JsonGateReportStore`**

Use safe key regex and QGate-owned root. Required methods: `save`, `load_key`, `list_reports`, `latest`.

- [ ] **Step 4: Write CLI smoke tests and implement**

Commands:

```text
qgate-final-gate evaluate --project ... --impact ... --scenario-plan ... --execution ... [--memory-recall ...] [--json]
qgate-final-gate show --report KEY [--json]
qgate-final-gate list
```

CLI paths are explicit local CLI inputs; the web API must not expose arbitrary path evaluation.

- [ ] **Step 5: Run Task 4 tests**

Run: `uv run pytest packages/final-gate/tests/test_ai.py packages/final-gate/tests/test_store.py packages/final-gate/tests/test_cli.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/final-gate
git commit -m "feat(final-gate): add explanation persistence and cli"
```

---

### Task 5: Workspace, API, and dashboard integration

**Files:**
- Modify: `pyproject.toml`
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/src/suitest_api/routers/final_gate.py`
- Modify: `apps/api/src/suitest_api/routers/projects.py`
- Test: `apps/api/tests/test_final_gate_api.py`
- Create: `apps/web/src/hooks/use-final-gate.ts`
- Create: `apps/web/src/routes/_app/gate.tsx`
- Create: `apps/web/src/routes/_app/gate.test.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Regenerate: `apps/web/src/routeTree.gen.ts`
- Modify: `.env.example`

**Interfaces:**
- API: read-only local authenticated report endpoints.
- Web: latest GateReport dashboard.

- [ ] **Step 1: Register workspace package**

Add `packages/final-gate` to uv workspace, source mapping, mypy path, pytest testpaths, and `qgate-final-gate` dependency to API package. Regenerate `uv.lock` locally.

- [ ] **Step 2: Write API tests first**

Test:
- authenticated local list/latest/detail;
- latest 404 when no report;
- invalid key 404;
- server mode hides endpoints with 404;
- API never accepts arbitrary filesystem evaluation path.

- [ ] **Step 3: Implement API router**

Conceptual routes:

```text
GET /api/v1/final-gate/reports
GET /api/v1/final-gate/latest
GET /api/v1/final-gate/reports/{key}
```

Use `SUITEST_FINAL_GATE_DIR=~/.qgate/final-gate`, local-mode guard, and `require_workspace_membership` consistent with existing QGate routers.

- [ ] **Step 4: Write web tests first**

Test:
- empty state;
- PASS card;
- BLOCK card distinguishes verified product failure;
- MANUAL card distinguishes environment/setup gap;
- required coverage and historical risk sections render;
- decision trace renders.

- [ ] **Step 5: Implement hook and `/gate` screen**

Dashboard sections exactly:
1. verdict + headline;
2. why this verdict;
3. blocking findings;
4. required coverage;
5. manual-review items;
6. historical QA risks;
7. evidence/decision trace.

- [ ] **Step 6: Add Sidebar navigation and regenerate TanStack route tree**

Add `Final Gate` under Insights with `/gate`.

- [ ] **Step 7: Run API/web tests**

Run:

```bash
uv run pytest apps/api/tests/test_final_gate_api.py -q
cd apps/web && npm test -- --run src/routes/_app/gate.test.tsx
npm run typecheck
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock apps/api apps/web .env.example
git commit -m "feat(final-gate): expose api and dashboard"
```

---

### Task 6: Documentation and full verification

**Files:**
- Create: `docs/FINAL_GATE.md`
- Modify: `docs/API.md`
- Modify: `docs/README.md` if index requires explicit subsystem entry
- Do not mark `QGATE_PROGRESS.md` complete before merge.

**Interfaces:**
- No new runtime interfaces; documents product workflow and contracts.

- [ ] **Step 1: Document technical/business workflow**

`docs/FINAL_GATE.md` must explain:
- input chain;
- decision matrix;
- BLOCK vs MANUAL distinction;
- required coverage policy;
- historical memory policy;
- AI non-authority;
- CLI/API/dashboard usage;
- V1 limits.

- [ ] **Step 2: Add Final Gate API section to `docs/API.md`**

Document exact read-only endpoints and local/auth behavior.

- [ ] **Step 3: Run Final Gate package tests**

Run: `uv run pytest packages/final-gate/tests -q`
Expected: 0 failures.

- [ ] **Step 4: Run affected Python tests**

```bash
uv run pytest packages/project-intelligence/tests packages/impact-analysis/tests packages/scenario-intelligence/tests packages/browser-execution/tests packages/qa-memory/tests packages/final-gate/tests apps/api/tests/test_final_gate_api.py -q
```

Expected: 0 failures.

- [ ] **Step 5: Run static checks**

```bash
uv run ruff check packages/final-gate apps/api/src/suitest_api/routers/final_gate.py apps/api/tests/test_final_gate_api.py
uv run mypy packages/final-gate/src apps/api/src/suitest_api/routers/final_gate.py
```

Expected: 0 errors.

- [ ] **Step 6: Run web verification**

```bash
cd apps/web
npm test -- --run src/routes/_app/gate.test.tsx
npm run typecheck
npm run build
```

Expected: PASS.

- [ ] **Step 7: Run final behavioral fixture matrix**

Verify at minimum:

1. verified checkout assertion failure => BLOCK;
2. required environment failure => MANUAL;
3. required state setup failure => MANUAL;
4. all required scenarios verified PASS => PASS;
5. zero required meaningful coverage => MANUAL;
6. input fingerprint mismatch => MANUAL;
7. strong historical regression unverified => MANUAL;
8. historical regression verified PASS => can PASS if all other required coverage passes;
9. optional P3 environment failure does not block PASS unless promoted;
10. BLOCK has precedence over simultaneous manual gaps in a valid chain.

- [ ] **Step 8: Visual smoke `/gate` locally**

Inspect PASS, BLOCK, and MANUAL fixtures. Confirm environment/setup gaps are not styled as product bugs and verdict is readable immediately.

- [ ] **Step 9: Self-review branch diff against spec**

Check:
- no verdict path can silently PASS missing required coverage;
- no QA Memory path directly creates BLOCK without current product evidence;
- no AI code mutates deterministic verdict/confidence upward;
- no web endpoint accepts arbitrary target filesystem paths;
- no unrelated Suitest refactor.

- [ ] **Step 10: Commit docs/final verification fixes**

```bash
git add docs packages/final-gate apps/api apps/web pyproject.toml uv.lock .env.example
git commit -m "docs(final-gate): document strict qa verdict workflow"
```

---

## Completion Gate

Before opening the PR, require fresh evidence for:

- Final Gate unit/integration tests;
- BLOCK/MANUAL/PASS fixture matrix;
- input-integrity fail-closed behavior;
- historical-memory obligation behavior;
- AI non-authority tests;
- API tests;
- dashboard tests + visual smoke;
- Ruff;
- mypy;
- web typecheck/build;
- affected upstream QGate tests;
- clean branch diff with no unrelated changes.

Only then open one `feat: Final Gate V1` PR. Do not merge or update `QGATE_PROGRESS.md` completion status until the normal Antigravity verification/merge workflow succeeds.
