# State-Aware Execution + Suitest Sync V1 Design

## Purpose

Fix validated QGate gaps discovered during the hidden wallet regression test:

1. Scenario Intelligence can identify a relevant semantic state but Browser Execution must establish that state before assertions.
2. QGate-generated scenarios must be visible as normal Suitest test cases.
3. Once the right route/state is reached, QGate must derive meaningful product assertions without hard-coding fixture-specific expected values.

The goal is to preserve QGate as the intelligence layer while using Suitest as the visible test-management/execution foundation.

## Success Criteria

For an impacted stateful change, QGate must be able to:

- represent the required runtime state explicitly,
- resolve a safe deterministic setup mechanism for that state,
- compile setup + verification + assertion steps into browser execution,
- fail closed as UNVERIFIED when the state cannot be established safely,
- persist executable QGate scenarios into Suitest as QGate-managed test cases,
- avoid duplicate test-case creation across repeated runs of the same scenario identity,
- preserve scenario/change/source identity in tags/metadata,
- make generated cases visible in the Suitest Tests UI,
- keep the target application read-only except for normal browser interactions,
- derive stable product assertions from deterministic baseline/runtime evidence,
- rerun the hidden regression fixture and produce a pipeline-owned assertion failure that Final Gate can BLOCK on.

## Non-Goals

V1 will not:

- hard-code wallet-specific logic, route names, fixture values, test ids, or expected currency amounts,
- infer arbitrary login credentials from secrets,
- mutate production source code,
- treat a raw screenshot baseline as sufficient truth,
- create permanent regression tests for every speculative scenario,
- replace QGate ScenarioPlan/ExecutionReport artifacts with Suitest rows,
- make Final Gate AI-dependent.

## Architecture

The flow becomes:

`ProjectKnowledge + ImpactReport -> ScenarioPlan -> Runtime State Resolution -> Route/State Passes -> Baseline Observation -> Assertion Synthesis -> State-Aware ScenarioCompiler -> Suitest Test Materializer -> Browser Execution -> ExecutionReport -> Final Gate`

QGate artifacts remain the canonical reasoning/evidence chain. Suitest test cases are a synchronized user-visible projection of executable QGate scenarios.

## 1. Runtime State Model

A state requirement is semantic and may resolve to one deterministic mechanism:

- UI control interaction,
- cookie set/remove,
- localStorage/sessionStorage set/remove,
- query parameter,
- deterministic URL/route variant,
- already-known authenticated fixture/profile,
- feature flag exposed through a deterministic project-controlled mechanism.

A resolved state setup includes semantic state identity, setup mechanism, bounded target/value data, a verification condition, evidence/source, confidence, and whether runtime verification is required.

Unknown or unsafe setup remains unresolved. Browser Execution must not guess.

## 2. State Resolution

Resolution order:

1. deterministic project evidence already discovered by Project Intelligence,
2. explicit runtime setup profile supplied by the user/project,
3. bounded browser discovery of obvious semantic controls when allowed,
4. optional AI semantic enrichment over bounded evidence,
5. unresolved -> UNVERIFIED.

The resolver must be general-purpose. No code may special-case the current fixture.

## 3. State-Aware Compilation

A scenario requiring a state should compile in this order:

1. navigate to an appropriate route,
2. establish required state,
3. verify required state is active,
4. execute scenario actions,
5. execute assertions,
6. capture evidence.

Cross-state scenarios compile into independent state passes. Mutually exclusive states must never be applied in one browser state. Passes aggregate back to the original logical scenario identity.

A scenario cannot be marked verified merely because the route loaded. If a required semantic state cannot be established or verified, the scenario is UNVERIFIED or BLOCKED_BY_GAP, never PASSED.

## 4. Suitest Test Materialization

QGate executable scenarios are projected into existing Suitest test-case semantics rather than a second test database.

Materialized test cases must be QGate-managed, traceable to scenario/project/change identity, idempotent for the same exact identity, executable through existing Suitest mechanisms, and visible in the existing Tests UI.

## 5. Idempotency and Lifecycle

Repeated materialization of the same scenario identity must update/reuse the existing QGate-managed test case rather than create duplicates.

Change-specific scenarios remain traceable to their change. Confirmed defects can later be promoted by QA Memory into durable regression coverage. Unresolved/manual scenarios are not treated as passing executable evidence.

## 6. Final Gate Integration

Final Gate behavior remains deterministic and unchanged in principle.

A product failure only BLOCKs when the current required scenario produced a verified pipeline-owned assertion failure. Manual browser inspection outside QGate execution cannot substitute for ExecutionReport evidence.

Required-state setup failure must prevent PASS for an important required scenario.

## 7. UI Behavior

No new major dashboard is required. Existing Suitest Tests UI shows materialized QGate-managed cases; QGate Scenario/Execution views continue to show reasoning and execution artifacts.

## 8. Error Handling / Fail-Closed Rules

- Required state unresolved -> UNVERIFIED, not PASS.
- State setup action fails -> STATE_SETUP_FAILURE.
- State verification fails -> STATE_SETUP_FAILURE or ASSERTION_FAILURE according to whether failure is setup vs product invariant.
- Assertion target/value cannot be grounded deterministically -> UNVERIFIED/MANUAL REVIEW, not fabricated PASS or fabricated BLOCK.
- Suitest materialization failure is separate and cannot fabricate execution evidence.
- Provider/AI failure cannot replace deterministic evidence or invent assertions.

## 9. Tests

At minimum test:

- UI-controlled semantic state compiles to setup + verify + assertion flow,
- cross-state scenarios compile into separate passes and aggregate correctly,
- unresolved required state becomes UNVERIFIED,
- route-only compilation cannot mark a stateful scenario verified,
- QGate scenario materializes visibly and idempotently into Suitest,
- deterministic semantic states survive AI enrichment,
- stronger route evidence beats affected-route list order,
- baseline-backed assertion synthesis identifies a stable observable target/value,
- dynamic/ambiguous observations are rejected rather than promoted,
- current build mismatch becomes ASSERTION_FAILURE,
- hidden regression reaches Final Gate BLOCK when the synthesized assertion fails.

Regression suites for Scenario Intelligence, Browser Execution, API, Final Gate, and existing Suitest behavior must continue to pass.

## 10. Validation Fixture

Use the corrected validation fixture unchanged:

- clean baseline commit: `f6f8d42674ee78adab2bbd2a2c31e163d4f4fb3a`
- buggy commit: `5217bea6f6b6fb5fe40054fd422e5aa2a9d6f1e5`
- target changed file: `app/shop-context.js`

The implementation must not rely on these literal values in production code.

Expected post-fix validation:

- relevant route/state identified,
- required state established and verified,
- stable baseline observable target discovered,
- clean baseline expected value captured from that same target/state,
- current/buggy build evaluates the same assertion target,
- mismatch becomes verified ASSERTION_FAILURE,
- Final Gate returns BLOCK,
- corresponding QGate-managed test remains visible in Suitest,
- no target-project modification.

## 11. Scope / Isolation

Prefer changes inside existing Scenario Intelligence, Browser Execution, evidence collection, and API/Suitest integration boundaries. Reuse current models/services where possible. Do not refactor unrelated upstream Suitest code. Do not alter local auth bypass or LLM configuration behavior.

## 12. Baseline-Backed Assertion Synthesis

Assertion synthesis is deterministic and evidence-bounded. It is not generic screenshot diffing and does not accept baseline output blindly as truth.

For each required route/state pass:

1. Execute the clean baseline using the exact same deterministic route and state setup contract intended for the changed build.
2. Collect bounded observable candidates from rendered DOM evidence. Prefer stable semantic locators such as test id, accessible label/name, role/name, or a uniquely resolved element. Record text/value and minimal structural metadata.
3. Rank candidate observables by relevance to impacted state/change evidence. State/change tokens may match nearby label text, target metadata, source evidence excerpts, affected symbols, and stable locator metadata. Dependency-only proximity is weaker than direct rendered relevance.
4. Reject candidates that are ambiguous, missing on either side, obviously volatile, or cannot be re-resolved uniquely on the changed build.
5. For a stable candidate, create an assertion contract containing locator metadata, baseline expected observable value, source route/state identity, and provenance showing why the target is relevant.
6. Compile that contract into existing Browser Execution assertions. The changed build must be evaluated against the baseline-derived expected value on the same route/state pass.
7. If the changed build differs, report a normal verified ASSERTION_FAILURE. Do not classify it as setup failure.

Baseline observation is state-specific. Values from one semantic state must not become expected values for another state unless a cross-state invariant explicitly proves they should match.

### Stability rules

A candidate is eligible only when:

- the locator is unique and deterministic,
- the target is present after state verification,
- the baseline observation succeeds consistently within the bounded validation run,
- the observable is a value/text/attribute suitable for exact or normalized comparison,
- evidence connects the target to the impacted behavior strongly enough to justify testing it.

A candidate is rejected when it includes obvious volatility such as timestamps, random ids, request-specific tokens, rotating content, or non-deterministic counters unless a project-specific deterministic contract already exists.

### Assertion provenance

Every synthesized assertion must preserve:

- scenario key,
- route,
- state key/pass identity,
- locator description,
- baseline expected value,
- baseline source fingerprint/ref,
- change source identity,
- supporting evidence/relevance reason.

This provenance must travel into compiled steps/evidence so Final Gate can distinguish a pipeline-owned product assertion from manual inspection.

### AI boundary

AI may help rank or explain already bounded candidates, but it cannot invent target selectors or expected values. The source of truth for synthesized expected values is deterministic baseline browser evidence plus project/change evidence.