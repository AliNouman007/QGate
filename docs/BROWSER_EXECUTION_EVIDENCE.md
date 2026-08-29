# Browser Execution & Evidence V1

Browser Execution & Evidence is QGate's runtime verification layer between Scenario Intelligence and later QA Memory / Final Gate.

## Pipeline

`ScenarioPlan -> ScenarioCompiler -> ExecutionRequest -> BrowserExecutor -> ExecutionReport`

The layer executes what can be executed safely and records what actually happened. It does **not** decide QGate's final `PASS`, `BLOCK`, or `MANUAL REVIEW REQUIRED` outcome.

## Why this layer is separate

Scenario Intelligence answers **what should be tested**. Browser Execution answers **what was actually executed and observed**. Keeping them separate lets QGate distinguish an application assertion mismatch from failures caused by credentials, environment, browser startup, navigation, target resolution, or an unsupported test definition.

## Scenario eligibility

- `ready`: compiled and executed when every required operation is safely supported.
- `runtime_discovery_required`: retained as `unverified`; V1 does not silently upgrade readiness.
- `manual_only`: recorded as `skipped_manual`.
- `blocked_by_gap`: recorded as `blocked`.

Existing human-readable Scenario Intelligence steps are compiled conservatively. Known routes become deterministic navigation operations. Explicit supported command patterns such as `Assert text "..."`, `Assert visible "..."`, `Assert hidden "..."`, `Click "..."`, `Fill "..." with "..."`, and `Capture ...` can be compiled. Ambiguous prose is not converted into AI-invented selectors.

## Execution status

Execution status is not Final Gate judgement:

- `passed`: supported required steps executed successfully.
- `failed`: the intended application state was reached and a deterministic assertion failed.
- `execution_error`: browser/test/config/environment prevented reliable completion.
- `unverified`: the scenario matters but cannot be safely reached/executed with current runtime knowledge.
- `skipped_manual`: Scenario Intelligence declared manual-only.
- `blocked`: a known gap prevents meaningful execution.

## Failure categories

V1 keeps failure category separate from status:

- `assertion_failure`
- `navigation_failure`
- `state_setup_failure`
- `target_resolution_failure`
- `test_definition_error`
- `environment_failure`
- `browser_failure`
- `network_infra_failure`
- `timeout`
- `unknown_execution_failure`

An `assertion_failure` is evidence for the later QA Judge. Browser Execution itself does not label it a product bug.

## Browser foundation

QGate reuses the existing Suitest lifecycle browser provisioning contract (`ensure_browser`) and Playwright runtime. Chromium is provisioned by the existing lifecycle layer rather than adding browser dependencies to the target repository.

The target project stays read-only.

## Target resolution

V1 only interacts with a target when trusted metadata can resolve it deterministically. Resolution favors semantic signals:

1. role + accessible name;
2. label;
3. existing test id;
4. exact visible text;
5. trusted supplied selector.

If a candidate strategy matches multiple elements, QGate does not choose one randomly. The scenario becomes unverified with `target_resolution_failure`.

## Evidence

Per-step evidence can contain:

- requested route and final URL;
- page title;
- relevant target DOM state;
- bounded target HTML excerpt;
- selected computed CSS properties;
- bounding box for relevant layout checks;
- console events;
- bounded/redacted network metadata;
- screenshot artifact references on failures/checkpoints;
- expected/actual values;
- timings and attempt history.

Large binary artifacts are referenced by path/hash instead of embedded in the JSON report.

## Redaction

Before persistence, Browser Execution omits or redacts sensitive values such as:

- Authorization and Cookie headers;
- passwords;
- access/refresh tokens and API keys;
- secret-like fields;
- payment-card/CVV-like fields;
- sensitive query parameters.

The structured report should never become a secret dump.

## Retry policy

V1 is conservative:

- deterministic assertion failures are not retried automatically;
- transient browser/navigation/infrastructure retry budget is at most one;
- previous attempts remain visible;
- runtime-discovery/setup failures are not blindly retried.

The implementation keeps `retry_budget` bounded to `0` or `1`. Further retry orchestration should only be added with evidence that it improves signal rather than hiding failures.

## Persistence

`JsonExecutionReportStore` persists QGate-specific `ExecutionReport` JSON outside the target repository, defaulting conceptually to:

`~/.qgate/browser-execution`

Artifact files live separately under the configured artifact directory.

Execution identity retains:

- Scenario Plan key;
- project source id/fingerprint;
- Impact change source id;
- execution configuration fingerprint;
- unique run id.

## CLI

Primary local command:

```text
qgate-browser-execution run \
  --scenario-plan /path/to/scenario-plan.json \
  --base-url http://127.0.0.1:3000
```

Useful filters/options include `--scenario`, `--priority`, `--json`, `--store-dir`, timeouts, headed mode, and a bounded retry budget.

## Local read-only API

The local API exposes persisted reports only:

- `GET /api/v1/browser-execution/reports`
- `GET /api/v1/browser-execution/latest`
- `GET /api/v1/browser-execution/reports/{key}`

Normal workspace authentication remains required. Server mode hides these local-store endpoints with 404. The browser API does not accept arbitrary filesystem paths or JavaScript for execution.

## Dashboard

`/execution` presents:

- selected vs executed scenario coverage;
- passed/failed/execution-error/unverified/manual/blocked counts;
- per-scenario status and verification flag;
- failure category;
- route and timings;
- per-step operation/result/expected/actual;
- console/network evidence counts;
- screenshot/artifact references;
- coverage gaps.

This view is evidence-oriented. It intentionally does not claim the final QGate verdict.

## Validation target

The real-browser integration fixture must demonstrate at minimum:

1. a READY scenario that passes in Chromium;
2. a deliberate text regression (`expected: You Pay`, `actual: Total`) producing `failed + assertion_failure` with evidence;
3. an unavailable/dead target producing `execution_error` with environment/navigation classification rather than assertion failure;
4. readiness preservation for runtime/manual/blocked scenarios;
5. evidence redaction and persistence round-trip.

## V1 limitations

- Existing Scenario Intelligence prose that lacks a deterministic executable operation may remain unverified.
- Runtime discovery is intentionally narrow; there is no unrestricted crawler/exploratory click agent here.
- Authentication/data setup only works when explicitly configured by safe existing runtime facilities.
- No financial/payment attempts or fabricated account/data setup.
- No full visual-diff judgement.
- No cross-browser matrix orchestration beyond the configured existing Playwright browser path.
- Failure category is not the final semantic product-bug classification; that belongs to the later Final Gate/QA Judge.
