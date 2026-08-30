# State-Aware Execution + Suitest Sync V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make QGate stateful scenarios establish their required browser state, synthesize grounded product assertions from stable clean-baseline evidence, and project executable QGate scenarios into visible, idempotent Suitest test cases.

**Architecture:** Keep ScenarioPlan/ExecutionReport as canonical QGate artifacts. Use deterministic state setup and route ranking to reach the correct surface, run clean-baseline observation for the same state pass, synthesize bounded assertions only from stable relevant DOM evidence, then execute the same assertion contract against the changed build. Fail closed when target/state/assertion evidence is ambiguous.

**Tech Stack:** Python, Pydantic, FastAPI, SQLAlchemy, Playwright, existing QGate Scenario Intelligence and Browser Execution packages, existing Suitest TestCaseService/repositories.

**Spec:** `docs/superpowers/specs/2026-08-29-state-aware-suitest-sync-v1-design.md`

## Global Constraints

- No wallet-, fixture-, route-, test-id-, or expected-value-specific production hard-coding.
- Required state unresolved or unverifiable must not PASS.
- Assertion target/value must come from deterministic project + browser evidence, not AI invention.
- Baseline output is usable only when the same target/state can be uniquely and stably re-resolved.
- QGate artifacts remain canonical; Suitest cases are a user-visible synchronized projection.
- Do not alter Final Gate decision policy unless a failing regression proves an actual policy bug.
- Do not modify the target application.

---

### Tasks 1-8

Existing state setup, Suitest sync, route ranking, multi-state pass aggregation, select setup, and lint tasks remain as previously implemented and validated on this branch.

### Task 9: Add baseline-backed deterministic assertion synthesis

**Files:**
- Modify: `packages/scenario-intelligence/src/qgate_scenario_intelligence/models.py` only if an assertion-candidate/contract type belongs in Scenario artifacts.
- Modify: `packages/scenario-intelligence/src/qgate_scenario_intelligence/generator.py` only for bounded assertion intent/relevance metadata, not runtime values.
- Modify: `packages/browser-execution/src/qgate_browser_execution/models.py`
- Modify/Create: focused assertion synthesis module under `packages/browser-execution/src/qgate_browser_execution/` following existing file-size/pattern conventions.
- Modify: `packages/browser-execution/src/qgate_browser_execution/compiler.py`
- Modify: `packages/browser-execution/src/qgate_browser_execution/executor.py`
- Modify: `packages/browser-execution/src/qgate_browser_execution/evidence.py` only if bounded DOM candidate capture cannot be expressed with current evidence.
- Test: `packages/scenario-intelligence/tests/test_generator.py`
- Test: `packages/browser-execution/tests/test_compiler.py`
- Test: `packages/browser-execution/tests/test_executor.py`
- Test: `packages/browser-execution/tests/test_browser_integration.py`
- Test: add a focused assertion-synthesis test file if responsibility is separated into a new module.

**Interfaces:**
- Consumes: current `ScenarioPlan`, selected route, state-pass identity/setup hints, `ImpactReport`/scenario evidence metadata, clean baseline URL/ref/fingerprint, and bounded rendered DOM evidence.
- Produces: deterministic `AssertionContract` objects containing target hint, comparison kind, expected baseline value, route/state identity, baseline provenance, and relevance reason.
- Compiler consumes `AssertionContract` and emits existing assertion operations (`ASSERT_TEXT`, `ASSERT_VALUE`, `ASSERT_ATTRIBUTE`) where possible.
- Executor evaluates the changed build against the contract and reports normal `ASSERTION_FAILURE` on mismatch.

- [ ] **Step 1: Write RED tests for candidate eligibility.** Create tests showing that a stable uniquely identifiable rendered value linked to impacted-state evidence becomes an assertion candidate, while ambiguous, duplicate, missing, or volatile observations are rejected.

- [ ] **Step 2: Write RED tests for state-specific baseline contracts.** Prove that baseline observations are keyed by original scenario + route + pass/state identity so one state's value cannot silently become another state's expectation.

- [ ] **Step 3: Add bounded assertion contract models.** Include scenario key, route, state/pass key, `TargetHint`, operation/comparison kind, expected baseline observable, source baseline fingerprint/ref, change source id, supporting evidence/relevance reason, and confidence/stability metadata. Do not add fixture literals.

- [ ] **Step 4: Implement deterministic DOM candidate collection.** After successful baseline navigation + state verification, collect a bounded set of uniquely resolvable visible output candidates. Prefer existing stable semantic locator metadata in this order where available: test id; accessible label/name/role; unique stable selector fallback. Capture normalized text/value/selected attribute as appropriate. Do not crawl the entire DOM without bounds.

- [ ] **Step 5: Implement volatility and ambiguity rejection.** Reject candidates with non-unique locators, missing/empty values without evidence of relevance, obvious timestamps/random identifiers/request tokens, or candidates that cannot be deterministically re-resolved. Keep rules conservative; uncertainty yields no assertion.

- [ ] **Step 6: Implement deterministic relevance ranking.** Build bounded relevance tokens from scenario reason/state label/state key/source impact evidence and rank observable candidates using direct token overlap with locator metadata, nearby rendered label/text, and supplied impacted evidence. Direct rendered/state-specific evidence outranks generic route/dependency evidence. Exact ties without a clear winner remain unresolved rather than choosing arbitrarily.

- [ ] **Step 7: Promote only stable high-confidence candidates into `AssertionContract`.** Preserve provenance showing baseline route/state/target/value and why the target is relevant. AI may explain/rank bounded candidates only if already supported, but cannot invent selector/expected value.

- [ ] **Step 8: Compile assertion contracts into existing browser operations.** Exact input/select value -> `ASSERT_VALUE`; visible text/output -> `ASSERT_TEXT` or a more precise existing assertion form; attribute contract -> `ASSERT_ATTRIBUTE` only if executor already supports it safely, otherwise keep the candidate unresolved instead of adding a broad new mechanism.

- [ ] **Step 9: Execute the same contract against the changed build.** Re-establish the exact same route/state pass in a clean context, resolve the same target, and compare to baseline expected value. A mismatch is `FAILED` + `ASSERTION_FAILURE`; target/setup/environment failures retain their existing classifications and cannot become product failures.

- [ ] **Step 10: Aggregate assertion failures correctly for multi-state scenarios.** Any verified product assertion failure in a required pass makes the original logical scenario FAILED. A missing/unverifiable assertion for an important required pass prevents PASS and remains UNVERIFIED/MANUAL according to existing fail-closed policy.

- [ ] **Step 11: Preserve assertion provenance in execution evidence/materialization.** Ensure current scenario/change/fingerprint/pass identity and baseline expected value are traceable in compiled/execution artifacts. Do not make Final Gate parse screenshots or infer expectations itself.

- [ ] **Step 12: Add end-to-end hidden-regression test/harness coverage.** Using generic fixture semantics, prove the pipeline can learn a stable baseline observable under a required state and then classify a changed-build mismatch as `ASSERTION_FAILURE` without manually injecting the expected value.

- [ ] **Step 13: Run full verification matrix.** Run Project Intelligence, agent, Scenario Intelligence, Browser Execution, Final Gate, relevant API/materializer tests, Ruff, and mypy. Fix only regressions attributable to this task; avoid unrelated refactoring.

- [ ] **Step 14: Rerun corrected hidden-wallet validation fixture unchanged.** Clean baseline `f6f8d42674ee78adab2bbd2a2c31e163d4f4fb3a`; bug commit `5217bea6f6b6fb5fe40054fd422e5aa2a9d6f1e5`. Required ideal result: relevant `/checkout` state pass established; a stable payable-related output chosen from generic relevance evidence; expected value comes from clean baseline; buggy build mismatch yields `ASSERTION_FAILURE`; Final Gate returns `BLOCK`; Suitest case remains visible; target shop unchanged.

- [ ] **Step 15: If ideal result is not reached, report all remaining blockers in one batch.** Do not inject a wallet-specific assertion, expected `$9.00`, selector, or route. Return stage/root cause/file-function for each remaining blocker so the next iteration stays batched.
