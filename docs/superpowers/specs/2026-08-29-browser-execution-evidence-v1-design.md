# Browser Execution & Evidence V1 Design

## Purpose

Browser Execution & Evidence V1 converts a persisted `ScenarioPlan` into real browser execution attempts using the existing Suitest/Playwright execution foundation, then records structured deterministic evidence for later QA Memory and Final Gate decisions.

This phase does **not** make the final PASS/BLOCK/MANUAL REVIEW REQUIRED decision. Its responsibility is narrower: execute what can be executed safely, preserve what could not be verified, and return trustworthy run/evidence records without confusing product failures with setup/environment failures.

## Product workflow

`ScenarioPlan`
→ select executable scenarios
→ compile Scenario steps into Suitest-compatible execution requests
→ resolve runtime setup/entry conditions
→ execute through existing Suitest/Playwright foundation
→ collect per-step and run-level evidence
→ classify execution outcome category
→ persist structured `ExecutionReport`
→ expose CLI/API/dashboard views
→ feed QA Memory and Final Gate.

The end-to-end QGate flow becomes:

`Project source`
→ `Project Intelligence`
→ `Impact Analysis`
→ `Scenario Intelligence`
→ `Browser Execution & Evidence`
→ `QA Memory`
→ `Final Gate`.

## Core principles

1. Reuse Suitest's existing browser runner, Playwright integration, evidence capture, run management, MCP and lifecycle capabilities wherever practical.
2. Do not build a second generic browser automation engine.
3. `ScenarioPlan` is planning truth; runtime browser evidence is execution truth.
4. Only sufficiently executable scenarios may be auto-run. Unknown or unsafe setup must not be guessed.
5. An assertion failure is not automatically a product bug; execution records must preserve the exact failure type and evidence for later judgement.
6. Environment, authentication, unavailable test data, selector-resolution, browser crash and infrastructure failures must remain distinguishable from application assertion failures.
7. Every run must be traceable back to scenario key, scenario plan identity, impact source and project fingerprint.
8. Evidence is structured first, artifact files second. Screenshots/videos alone are not enough.
9. Blind retries must not hide deterministic failures.
10. Target repositories remain read-only; QGate must not inject test dependencies/config into them unless explicitly approved.
11. The LLM is not required for normal execution. AI may later help runtime discovery/classification only inside strict evidence-bounded contracts.
12. V1 remains frontend/browser focused and general-purpose.

## Scope

Browser Execution & Evidence V1 is one complete feature PR and includes:

- structured execution contracts (`ExecutionRequest`, `ExecutionReport`, `ScenarioExecution`, `StepExecution`, evidence records and outcome categories);
- selection of executable Scenario Intelligence outputs;
- compilation/adaptation from `Scenario`/`ScenarioStep` into the existing Suitest execution/test semantics;
- execution through existing Suitest/Playwright/lifecycle primitives rather than a replacement engine;
- deterministic page navigation and assertion execution for supported structured actions;
- safe runtime target/element resolution where existing Suitest/Playwright mechanisms can support it;
- explicit unsupported/unresolved step handling;
- browser evidence capture: URL/navigation, DOM/element snapshots, visible text/value/state where relevant, computed CSS where relevant, console events, network events/errors, screenshot references, timing and run logs;
- linkage to existing video/trace artifacts when the current Suitest runner already produces them;
- execution outcome classification that separates assertion/application failures from setup/config/environment/runtime infrastructure failures;
- controlled retry policy;
- persisted QGate-owned execution reports/index metadata while reusing Suitest artifact storage where practical;
- human-readable CLI/API/dashboard views;
- realistic browser integration fixtures including one deliberate application regression and one environment/setup failure;
- documentation and verification tests.

## Non-goals

V1 does not include:

- final PASS/BLOCK/MANUAL REVIEW REQUIRED judgement;
- permanent QA Memory/history learning;
- automatic production-code fixes;
- unrestricted autonomous browser exploration across the entire application;
- automatic credential generation;
- automatic creation of financial/payment/test-user data;
- bypassing authentication/security controls;
- assuming runtime reachability from static evidence;
- full general NLP-to-Playwright code generation;
- mobile/Appium execution;
- cross-browser matrix orchestration beyond the existing supported/default browser path unless it is already trivial in Suitest;
- treating screenshot pixel differences alone as product defects.

## Inputs

### Required input

One persisted `ScenarioPlan` whose project/source identity remains valid.

Each execution must retain:

- Scenario Plan stable key/id;
- project source id;
- project fingerprint;
- impact change source id;
- scenario key;
- scenario priority/readiness/kind;
- scenario evidence/source impact keys.

### Runtime configuration

Execution needs a local/test target base URL or equivalent existing Suitest target configuration.

Configuration may include:

- base URL;
- browser choice if existing runner supports it;
- global timeout;
- per-step timeout;
- artifact/evidence policy;
- optional known state setup/profile references;
- retry budget.

Secrets/credentials must be references to existing protected configuration, never copied into `ScenarioPlan` or execution artifacts.

## Scenario eligibility

Scenario Intelligence readiness remains authoritative for automatic selection.

### `READY`

Eligible for automatic compilation/execution if every required step maps to a supported execution operation.

### `RUNTIME_DISCOVERY_REQUIRED`

Not automatically treated as executable success/failure.

V1 may attempt only **bounded safe discovery** if explicitly supported by deterministic runtime data (for example, confirming a known route exists or locating an element by robust semantic role/text derived from the scenario). If required setup remains unknown, outcome is `UNVERIFIED` with a discovery/setup reason.

### `MANUAL_ONLY`

Do not auto-run. Record as unexecuted/manual-required.

### `BLOCKED_BY_GAP`

Do not auto-run. Preserve the blocking gap in the Execution Report.

Scenario readiness must never be silently upgraded by the execution layer.

## Execution contracts

### `ExecutionPlanRun`

Represents one attempt to execute a Scenario Plan.

Minimum fields:

- stable run id/key;
- Scenario Plan key;
- project source id/fingerprint;
- impact change source id;
- started/completed timestamps;
- runtime target identifier/base URL (redacted/safe representation where required);
- selected scenario count;
- executed/unverified/manual/blocked counts;
- pass/fail/error counts;
- scenario execution records;
- run-level evidence/artifact references;
- execution coverage gaps;
- runner/version metadata.

### `ScenarioExecution`

Minimum fields:

- scenario key/title/kind/priority;
- source Scenario Plan key;
- execution status;
- failure category where applicable;
- started/completed timestamps and duration;
- target route/url;
- precondition/setup result;
- ordered step execution records;
- evidence references;
- console/network summaries;
- screenshot/video/trace references where produced;
- retry attempts;
- deterministic reason/detail;
- `verified: bool`.

### `StepExecution`

Minimum fields:

- step index;
- source action/expected text;
- compiled operation kind;
- operation target metadata;
- result status;
- actual observed value/state where relevant;
- assertion expectation;
- timing;
- evidence captured before/after/failure;
- failure category/detail.

## Execution status model

Keep execution result separate from final QA judgement.

Suggested scenario-level statuses:

- `PASSED` — all required supported assertions/actions executed and passed;
- `FAILED` — execution reached the application state and at least one deterministic application assertion failed;
- `EXECUTION_ERROR` — automation could not reliably complete because of test/config/browser/environment/tooling failure;
- `UNVERIFIED` — scenario matters but could not be safely executed/reached with available runtime information;
- `SKIPPED_MANUAL` — Scenario Intelligence explicitly marked it manual-only;
- `BLOCKED` — execution is blocked by a known ScenarioPlan/project/runtime gap before meaningful verification.

These are **not** QGate Final Gate outcomes.

## Failure categories

Execution must preserve an explicit failure category independent of status.

V1 categories should include a small useful set:

- `ASSERTION_FAILURE` — expected application behavior did not match observed behavior after reaching the intended state;
- `NAVIGATION_FAILURE` — intended route could not be opened/loaded as expected;
- `STATE_SETUP_FAILURE` — required precondition/session/auth/data state could not be established;
- `TARGET_RESOLUTION_FAILURE` — required interactive/observable target could not be resolved safely;
- `TEST_DEFINITION_ERROR` — compiled scenario instruction is invalid/unsupported/contradictory;
- `ENVIRONMENT_FAILURE` — target app/server/browser dependency unavailable or broken outside the assertion under test;
- `BROWSER_FAILURE` — Playwright/browser crash/startup/runtime infrastructure failure;
- `NETWORK_INFRA_FAILURE` — infrastructure/connectivity failure preventing meaningful verification;
- `TIMEOUT` — timeout with stage/context preserved;
- `UNKNOWN_EXECUTION_FAILURE` — last resort only, with raw deterministic context retained.

Later QA Judge/Final Gate may interpret `ASSERTION_FAILURE` as a likely product bug when evidence is sufficient. This V1 layer must not make that final semantic leap.

## Scenario → execution compilation

Scenario Intelligence outputs structured human-readable steps, not raw Playwright.

Browser Execution introduces an explicit compiler/adapter.

### Supported V1 operation kinds

Prefer a small deterministic operation vocabulary that maps cleanly onto existing Playwright/Suitest primitives:

- `NAVIGATE` — open a known route/URL;
- `CLICK` — interact with a safely resolved control;
- `FILL` — enter non-secret supplied/configured test data;
- `SELECT` — choose an option where deterministic target/value is known;
- `ASSERT_VISIBLE` / `ASSERT_HIDDEN`;
- `ASSERT_TEXT`;
- `ASSERT_VALUE`;
- `ASSERT_URL`;
- `ASSERT_ATTRIBUTE` when evidence clearly supports it;
- `ASSERT_LAYOUT_STATE` for bounded computed-style/geometry facts where deterministic expectations exist;
- `CAPTURE` — explicit evidence checkpoint;
- `COMPARE_STATE` — orchestrate two already-defined state executions and record relational evidence, without inventing exact pixel expectations.

Do not support arbitrary JavaScript snippets from Scenario Intelligence in V1.

### Compilation policy

A scenario is automatically executable only if all required steps can be mapped without inventing missing selectors, credentials, values or assertions.

If a step cannot be compiled safely:

- keep the scenario in the report;
- mark it `UNVERIFIED` or `EXECUTION_ERROR` depending on whether the problem is missing runtime knowledge vs malformed compiled test definition;
- record the exact unsupported operation/reason;
- do not guess.

## Runtime target/element resolution

Selectors are a major reliability risk.

V1 resolution priority should favor robust semantic strategies already supported by Playwright/Suitest:

1. explicit stable target metadata already present in a trusted existing execution/test contract;
2. accessible role + name;
3. associated label;
4. stable test id if the target app already provides one;
5. exact/normalized visible text when semantically safe;
6. bounded DOM relationship inferred from deterministic evidence;
7. CSS selector only when already supplied by trusted existing execution data or uniquely verified at runtime.

Avoid selectors based primarily on generated CSS class names, nth-child position, brittle deep DOM paths or AI-invented selectors.

If multiple candidate elements match and QGate cannot deterministically disambiguate them, do not click one at random; record `TARGET_RESOLUTION_FAILURE` or `UNVERIFIED`.

## Runtime state setup

Preconditions may require login, feature state, storage/session values, viewport or known data.

V1 supports only setup that is explicit and safely configurable, for example:

- navigate to base route;
- viewport size from a deterministic responsive scenario;
- preconfigured authenticated storage/session state already available through existing Suitest/Playwright facilities;
- existing test account secret reference;
- deterministic localStorage/cookie setup only when the scenario/project evidence explicitly identifies it and policy allows it;
- fixed fixture data in QGate-owned test fixtures.

Do not fabricate accounts, passwords, wallet balances, payment data or server-side business state.

Unknown required setup results in `UNVERIFIED` / `STATE_SETUP_FAILURE`, not a fake assertion failure.

## Evidence model

Evidence is collected per relevant step and run.

### Navigation/runtime evidence

- requested route;
- final URL;
- HTTP/navigation status where available;
- redirects;
- page load timing;
- document title when useful.

### DOM/element evidence

For targets involved in assertions/actions:

- semantic locator description;
- tag/role/name/label/test id where available;
- relevant text/value;
- visibility/enabled/checked/selected state;
- bounded HTML/DOM excerpt;
- element bounding box when layout is relevant;
- relevant computed CSS properties for layout/style assertions.

Do not dump the unrestricted entire DOM for every step.

### Console evidence

Collect structured console events with:

- level;
- text/message;
- source/location where available;
- timestamp.

Default report emphasizes errors/warnings generated during the scenario window while retaining bounded raw evidence.

### Network evidence

Collect bounded request/response metadata needed for QA:

- method;
- redacted URL;
- resource type;
- status;
- timing;
- failure reason;
- whether initiated during relevant step.

Do not persist authorization headers, cookies, request bodies containing secrets, payment data or unrestricted personal data.

### Visual evidence

Capture screenshots at minimum:

- scenario start/meaningful checkpoint when useful;
- assertion failure;
- unexpected runtime error where a page is visible.

Reuse existing Suitest screenshot/video/trace artifact handling where available.

V1 does not make a product failure solely from image similarity/pixel diff.

## Evidence redaction and safety

Evidence collection must redact or omit:

- authorization/cookie headers;
- passwords and secret input values;
- OAuth tokens/API keys;
- payment card/bank details;
- configured secret environment values;
- obvious sensitive request payload fields.

Artifacts should point to existing Suitest/QGate artifact storage. Structured ExecutionReport should store references, hashes/metadata and bounded observations rather than embedding large binary blobs.

## Retry policy

Retries are conservative.

Default V1 policy:

- deterministic `ASSERTION_FAILURE`: no automatic retry by default;
- obvious transient navigation/browser/infrastructure failure: at most one controlled retry when configured;
- runtime discovery/setup failure: no repeated blind retry;
- every retry is recorded as a separate attempt with reason;
- final execution status preserves previous attempt history.

A retry must never turn the historical first failure invisible.

## Cross-state execution

For `CROSS_STATE_COMPARISON` scenarios:

- execute each defined state independently when both are executable;
- capture comparable evidence at the same logical checkpoint;
- record both state observations;
- evaluate only explicit relational expectations supported by Scenario Intelligence (for example required visibility/label/layout relationship);
- if one state cannot be established, the comparison is `UNVERIFIED`, not passed by the other state.

## Bounded runtime discovery

V1 runtime discovery is intentionally narrow.

Allowed examples:

- verify a known route resolves;
- inspect a bounded page for a semantically named control referenced by the scenario;
- choose among candidate semantic locators when exactly one candidate matches deterministic scenario context;
- report discovered target metadata for the execution record.

Not allowed:

- unrestricted crawling;
- submitting destructive forms;
- purchasing/checkout/payment attempts without explicit safe test environment setup;
- guessing credentials;
- changing persistent production state;
- treating exploratory clicks as verification.

## Existing Suitest integration

Before implementing new browser code, inspect and reuse current capabilities in:

- runner/execution layer;
- Playwright/frontend lifecycle/runtime modules;
- blackbox execution components;
- MCP execution tools;
- evidence/artifact capture;
- test/run management;
- failure context and run result models.

Add QGate-specific adapters/contracts around those capabilities rather than moving or rewriting the existing framework wholesale.

If existing Suitest semantics conflict with QGate's strict execution/evidence contract, isolate the compatibility mapping in a small adapter layer.

## Persistence

Structured Browser Execution reports live in QGate-owned storage or existing Suitest run storage where the latter already provides the required durable model.

V1 decision rule:

- reuse existing Suitest run/artifact records for raw execution/artifacts;
- persist a QGate `ExecutionReport` projection/index only for ScenarioPlan traceability and QGate-specific outcome/evidence metadata not already represented cleanly.

Stable identity should include ScenarioPlan key + project fingerprint + execution configuration fingerprint + run/attempt identity.

Target repository is never used as persistence.

## CLI

Provide a local developer command conceptually like:

`qgate-browser-execution run --scenario-plan <plan.json> --base-url <url>`

Useful options may include:

- `--scenario <key>` to run one scenario;
- `--priority P0,P1` filter;
- `--ready-only` default behavior;
- `--json` report output;
- `--store-dir` QGate-owned report path;
- timeout/retry controls within safe bounds.

CLI must clearly report scenarios skipped as manual/blocked/unverified.

## Local API

Expose read-only local-mode execution-report endpoints following current QGate patterns:

- list execution reports/runs;
- latest execution report;
- detail by stable run key;
- optional scenario-execution detail if useful.

Actual execution triggering may remain CLI/service-only in V1 unless the existing Suitest run API provides a clean authenticated path to reuse. Do not add a browser endpoint that accepts arbitrary local filesystem paths or arbitrary JavaScript.

Normal workspace authentication remains required. Server mode stays hidden/404 unless explicitly supported later.

## Dashboard

Add a QGate execution/evidence view, likely `/execution` or `/evidence`, chosen to fit existing navigation.

The dashboard should answer:

- Which planned scenarios were selected?
- Which actually executed?
- Which passed assertions?
- Which failed assertions?
- Which were unverified/manual/blocked?
- Why did each failure occur?
- What deterministic evidence was captured?
- What screenshots/videos/traces exist?
- Were console/network errors observed?
- Was a retry used?
- What coverage remains unverified?

Do not present execution `PASSED` as QGate final PASS.

## Error handling

### ScenarioPlan mismatch/staleness

If plan project/source fingerprint does not match expected execution project/runtime context where validation is possible, fail closed.

### Base URL unavailable

Record run/scenarios as environment/blocked/unverified according to whether any meaningful browser verification occurred. Do not convert this into application assertion failures.

### Unsupported Scenario step

Record explicit unsupported/test-definition detail. Do not generate arbitrary code to force execution.

### Browser crash

Classify as `BROWSER_FAILURE`; preserve logs/artifacts and previous completed step evidence.

### Network outage

If it prevents intended page/application verification, classify infrastructure/environment rather than product bug unless the scenario explicitly tests handling of that controlled network failure.

### Assertion failure

Capture actual value/state + expected value + target evidence + screenshot, and classify `ASSERTION_FAILURE`.

### Partial execution

If required steps remain unexecuted, scenario cannot be `PASSED`.

## Testing strategy

### Unit tests

Cover:

- scenario readiness filtering;
- Scenario → operation compilation;
- unsupported operation behavior;
- stable locator strategy ordering;
- ambiguous target resolution handling;
- status/failure-category mapping;
- evidence redaction;
- retry policy;
- partial execution never passing;
- cross-state incomplete comparison handling;
- report identity/serialization/persistence.

### Browser integration fixture

Create a small deterministic frontend fixture served locally with:

- a normal route;
- interactive control;
- visible text/value assertion;
- two meaningful UI states;
- console error trigger;
- network request endpoint;
- deliberate application regression;
- missing/ambiguous target case.

Verify:

1. READY scenario executes through real Playwright/Suitest foundation;
2. navigation/action/assertion pass path produces `PASSED` with evidence;
3. deliberate wrong application label/value produces `FAILED + ASSERTION_FAILURE` with actual vs expected evidence and screenshot;
4. missing test server or impossible auth/setup produces `EXECUTION_ERROR`/`UNVERIFIED`, not assertion failure;
5. ambiguous locator does not click randomly;
6. console/network metadata are captured and redacted;
7. cross-state execution records both states;
8. screenshot/artifact references exist where expected;
9. plan/scenario/run traceability remains intact;
10. target fixture source is not modified by QGate.

### Existing Suitest regression tests

Run affected lifecycle/runner/MCP/API/web tests to prove QGate adapters do not break upstream execution behavior.

### API/web tests

- empty execution state;
- list/latest/detail reads;
- authentication preserved;
- server-mode hidden behavior;
- dashboard renders status/failure category/evidence/artifacts/coverage;
- web typecheck/build;
- visual smoke with pass/fail/unverified examples.

## Success criteria

Browser Execution & Evidence V1 is complete when QGate can take a verified ScenarioPlan and, on a controlled real frontend target:

1. automatically select and execute supported READY scenarios;
2. reuse real Suitest/Playwright execution rather than a mock engine;
3. correctly perform supported navigation/action/assertion operations;
4. capture deterministic per-step browser evidence;
5. capture useful screenshot, DOM/element, console, network and timing evidence without leaking secrets;
6. distinguish application assertion failure from setup/config/environment/browser failures;
7. leave runtime/manual/blocked scenarios visibly unverified instead of falsely passing them;
8. preserve full ScenarioPlan → Scenario → Execution → Evidence traceability;
9. persist/read a structured ExecutionReport;
10. expose a concise developer-facing execution/evidence view;
11. prove with a deliberate frontend regression that QGate records the actual mismatch correctly;
12. prove with an environment/setup failure that QGate does **not** misreport it as a product assertion failure.

## Relationship to later phases

### QA Memory

QA Memory will consume confirmed execution findings and human classifications. Browser Execution only supplies evidence and structured outcomes.

### Final Gate

Final Gate will combine Scenario priority/coverage + ExecutionReport + QA Memory to decide exactly one of:

- `PASS`
- `BLOCK`
- `MANUAL REVIEW REQUIRED`

Therefore Browser Execution must never silently erase unverified critical scenarios or prematurely issue a final gate decision.
