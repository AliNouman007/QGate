# State-Aware Execution + Suitest Sync V1 Design

## Purpose

Fix two validated QGate gaps discovered during the hidden wallet regression test:

1. Scenario Intelligence can identify a relevant semantic state (for example, `Logged In + Wallet`) but Browser Execution V1 may compile only route navigation/capture and fail to establish that state before assertions.
2. QGate-generated scenarios are persisted as QGate JSON `ScenarioPlan` artifacts, so they are not visible as normal Suitest test cases in the Suitest Tests UI.

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
- rerun the existing wallet regression fixture and produce a pipeline-owned assertion failure that Final Gate can BLOCK on.

## Non-Goals

V1 will not:

- hard-code wallet-specific logic,
- infer arbitrary login credentials from secrets,
- mutate production source code,
- create permanent regression tests for every speculative scenario,
- replace QGate ScenarioPlan/ExecutionReport artifacts with Suitest rows,
- make Final Gate AI-dependent.

## Architecture

The flow becomes:

`ProjectKnowledge + ImpactReport -> ScenarioPlan -> Runtime State Resolution -> State-Aware ScenarioCompiler -> Suitest Test Materializer -> Browser Execution -> ExecutionReport -> Final Gate`

QGate artifacts remain the canonical reasoning/evidence chain. Suitest test cases are a synchronized user-visible projection of executable QGate scenarios.

## 1. Runtime State Model

Introduce an explicit state-setup contract consumed by Browser Execution. A state requirement is semantic (for example `user=wallet`, `experiment=variant-b`) and may resolve to one deterministic mechanism:

- UI control interaction,
- cookie set/remove,
- localStorage/sessionStorage set/remove,
- query parameter,
- deterministic URL/route variant,
- already-known authenticated fixture/profile,
- feature flag exposed through a deterministic project-controlled mechanism.

A resolved state setup includes:

- semantic state key/value,
- setup mechanism,
- bounded target/value data required to perform the setup,
- a verification condition proving the state is active,
- evidence/source showing why this mechanism is valid,
- confidence and whether runtime verification is required.

Unknown or unsafe setup remains unresolved. Browser Execution must not guess.

## 2. State Resolution

Add a focused resolver between ScenarioPlan and ScenarioCompiler. It consumes Scenario state/precondition information plus bounded ProjectKnowledge/runtime discovery evidence.

Resolution order:

1. deterministic project evidence already discovered by Project Intelligence,
2. explicit runtime setup profile supplied by the user/project,
3. bounded browser discovery of obvious semantic controls when allowed,
4. optional AI semantic enrichment over bounded evidence,
5. unresolved -> UNVERIFIED.

The resolver must be general-purpose. No code may special-case `wallet`, `qgate-test-shop`, or the current fixture.

## 3. State-Aware Compilation

Extend Browser Execution operations only where needed to support safe state setup. Reuse existing CLICK/FILL/NAVIGATE/assertion operations whenever possible; add storage/cookie/query setup operations only if the existing executor cannot express them safely.

A scenario requiring a state should compile in this order:

1. navigate to an appropriate route,
2. establish required state,
3. verify required state is active,
4. execute scenario actions,
5. execute assertions,
6. capture evidence.

A scenario cannot be marked verified merely because the route loaded. If a required semantic state cannot be established or verified, the scenario is UNVERIFIED or BLOCKED_BY_GAP, never PASSED.

## 4. Suitest Test Materialization

Add a QGate-to-Suitest materializer that converts executable QGate scenarios into existing Suitest `TestCaseCreate` / step semantics rather than creating a second test database.

Materialized test cases must:

- live in a designated QGate-managed suite for the target project,
- use existing Suitest test-case APIs/service/repositories,
- have human-readable names based on scenario title/state,
- carry QGate tags including scenario key, project fingerprint, change source id, and management marker,
- map compiled steps to Suitest steps,
- remain executable under LOCAL/CLOUD tier,
- be discoverable in the existing Tests UI.

Suggested management tags:

- `qgate-managed`
- `qgate-scenario:<scenario-key>`
- `qgate-change:<change-source-id>`
- `qgate-project:<project-fingerprint>`

Exact tag encoding must respect existing tag constraints.

## 5. Idempotency and Lifecycle

Repeated materialization of the same scenario identity must update/reuse the existing QGate-managed test case rather than create duplicates.

Lifecycle policy:

- change-specific scenarios remain QGate-managed and traceable to their change,
- confirmed defects can later be promoted by QA Memory into durable regression coverage,
- speculative/manual/unresolved scenarios are not materialized as executable passing tests,
- stale QGate-managed cases are never silently treated as evidence for the current fingerprint/change.

No destructive cleanup is required in V1; stale cases may remain visible but must be clearly tagged and excluded from current execution unless identity matches.

## 6. Final Gate Integration

Final Gate behavior remains deterministic and unchanged in principle.

The critical requirement is evidence provenance: a product failure only BLOCKs when the current required scenario produced a verified pipeline-owned assertion failure. Manual browser inspection performed outside the compiled QGate execution cannot be substituted as current ExecutionReport evidence.

Required-state setup failure must prevent PASS for an important required scenario.

## 7. UI Behavior

No new major dashboard is required for V1.

Existing Suitest Tests UI should show materialized QGate-managed cases. Existing QGate Scenario/Execution pages continue to show QGate artifacts.

This gives users two complementary views:

- QGate views: why the scenario exists and how it relates to impact/change,
- Suitest Tests: the concrete executable test case and steps.

## 8. Error Handling / Fail-Closed Rules

- Required state unresolved -> UNVERIFIED, not PASS.
- State setup action fails -> STATE_SETUP_FAILURE.
- State verification fails -> STATE_SETUP_FAILURE or ASSERTION_FAILURE according to whether failure is setup vs product invariant.
- Suitest materialization failure must be reported separately and must not fabricate execution evidence.
- Duplicate-sync ambiguity -> reuse/update only when the QGate scenario identity tag matches exactly; otherwise create a distinct case.
- Provider/AI failure -> deterministic state evidence may continue; AI failure must not turn unresolved state into READY.

## 9. Tests

At minimum add tests for:

- UI-controlled semantic state compiles to setup + verify + assertion flow,
- localStorage/cookie/query mechanisms if implemented in V1,
- unresolved required state becomes UNVERIFIED,
- route-only compilation cannot mark a stateful scenario verified,
- QGate scenario materializes into an existing Suitest test case with steps/tags,
- repeated materialization is idempotent,
- changed scenario identity creates/updates the correct case without contaminating another change,
- materialized test appears through existing test-case read/list API,
- hidden wallet regression fixture reaches the wallet state through pipeline-owned execution,
- the resulting assertion failure reaches Final Gate and yields BLOCK.

Regression suites for Scenario Intelligence, Browser Execution, API, Final Gate, and existing Suitest test-case behavior must continue to pass.

## 10. Validation Fixture

Use the existing test project and existing hidden regression unchanged:

- clean baseline commit: `1ed1d06f01681a69ffbd5388771da512c61affd6`
- buggy commit: `40cf5de975eb6b0c8779a163acebf44b92fa885d`
- target changed file: `app/shop-context.js`

The implementation must not rely on these literal values in production code. They are validation-only fixtures.

Expected post-fix validation:

- checkout/wallet impact identified,
- wallet scenario generated,
- wallet state actually established by compiled pipeline execution,
- incorrect final payable produces verified assertion failure,
- evidence belongs to that scenario/change/fingerprint,
- Final Gate returns `BLOCK`,
- corresponding QGate-managed test case is visible in Suitest Tests UI,
- no target-project modification beyond the already existing intentional bug branch.

## 11. Scope / Isolation

Prefer changes inside the existing Scenario Intelligence, Browser Execution, and API/Suitest test-case integration boundaries. Reuse current Suitest repositories/services and current QGate models where possible. Do not refactor unrelated upstream Suitest code. Do not alter the existing local auth bypass or LLM configuration behavior.