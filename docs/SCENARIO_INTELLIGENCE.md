# QGate Scenario Intelligence V1

## Purpose

Scenario Intelligence answers the question **“given what changed and what can be affected, what should QGate test?”**

It consumes the merged `ProjectKnowledge` and `ImpactReport` contracts and produces a structured `ScenarioPlan`. It does not execute a browser, write Playwright code, classify runtime failures, or decide PASS/BLOCK/MANUAL REVIEW REQUIRED.

## Product flow

```text
ProjectKnowledge + ImpactReport
        ↓
evidence-backed impacted routes/states
        ↓
bounded scenario candidate generation
        ↓
priority + reachability/readiness
        ↓
duplicate collapse
        ↓
cross-state comparisons where justified
        ↓
optional bounded AI wording enrichment
        ↓
persisted ScenarioPlan
        ↓
future Suitest/Playwright execution
```

The important boundary is that **Impact Analysis determines what may be affected; Scenario Intelligence determines what to test; the execution phase later determines what actually happens in the browser.**

## Package ownership

Core implementation lives in:

- `packages/scenario-intelligence/src/qgate_scenario_intelligence/models.py` — public Scenario Plan contracts.
- `generator.py` — deterministic scenario generation.
- `state_expansion.py` — bounded evidence-backed state families/pairs.
- `prioritization.py` — deterministic priority/readiness rules.
- `signature.py` — duplicate signatures and conservative merge rules.
- `store.py` — QGate-owned JSON persistence.
- `report.py` / `cli.py` — local developer output.
- `semantic.py` — bounded evidence packs for optional AI enrichment.

Provider-backed enrichment lives in `packages/agent/src/suitest_agent/scenario_intelligence_semantic.py` so deterministic Scenario Intelligence does not depend on an LLM.

Local read-only API lives in `apps/api/src/suitest_api/routers/scenario_intelligence.py`.

Dashboard UI lives in `apps/web/src/routes/_app/scenarios.tsx` and `apps/web/src/hooks/use-scenario-intelligence.ts`.

## Inputs and snapshot safety

`ScenarioGenerator.generate(project_knowledge, impact_report)` requires:

- matching `project_source_id`;
- matching project fingerprint.

A mismatch raises `ScenarioInputMismatchError`. QGate does not silently mix an Impact Report from one source snapshot with Project Intelligence from another.

## ScenarioPlan contract

A plan contains:

- metadata: project source/fingerprint, impact change source, versions/timestamp;
- generation budget;
- summary counts;
- ordered scenarios;
- cross-state groups;
- coverage gaps.

Each scenario carries:

- stable key;
- title and explicit kind;
- `P0`–`P3` priority;
- confidence;
- route/target/state references;
- preconditions;
- structured action + expected-outcome steps;
- reason;
- source Impact Analysis keys;
- evidence;
- automation readiness;
- runtime-discovery/manual warnings;
- optional cross-state group and AI explanation.

Scenario steps deliberately do **not** contain invented selectors or raw browser code. `target_kind` defaults to `FE_WEB`, matching the current frontend-focused V1 and remaining compatible with later Suitest adaptation.

## Scenario kinds

V1 uses a deliberately small set:

- `smoke` — direct impacted route/surface check;
- `route_regression` — deterministic dependent route check;
- `state_variant` — evidence-backed impacted state;
- `negative_state` — evidence-backed denied/error/empty/absent-style state;
- `cross_state_comparison` — compare related states on the same impacted UI surface;
- `runtime_discovery` — important coverage that cannot yet be safely reached/proven from static evidence.

## State expansion

State expansion is bounded and evidence-first. It uses the existing semantic states in `ProjectKnowledge`; it does not generate every theoretical state combination.

States are grouped by evidence surface and semantic state kind. Related pairs may be recognized from complementary evidence-backed labels such as authenticated/unauthenticated, present/absent, enabled/disabled, loaded/loading, success/error, allowed/denied, desktop/mobile, or with/without forms.

The generator only creates a cross-state comparison when:

1. the impacted change is UI/styling/state/responsive/shared-sensitive;
2. at least two related states are already represented in project evidence;
3. the state family is connected to impacted evidence;
4. a concrete impacted route can be associated.

This is designed to catch regressions such as a component looking correct in one state but breaking layout or behavior in another.

## Priority

Priority is deterministic-first and is not business severity.

- direct + high-confidence impact ranks above indirect impact;
- broad shared reuse can raise direct coverage urgency;
- possible/unknown coverage ranks lower for execution but stays visible;
- QGate does not claim financial/business severity unless future evidence/profile data explicitly supplies it.

The output uses `P0`, `P1`, `P2`, and `P3` so it can later map cleanly into existing Suitest test-case priority semantics.

## Automation readiness

Readiness is separate from test result:

- `ready` — route/action/assertion intent is concrete enough for execution to attempt;
- `runtime_discovery_required` — the scenario matters, but state setup/reachability needs browser discovery;
- `manual_only` — reserved for scenarios that cannot safely be represented as automated browser coverage;
- `blocked_by_gap` — required evidence is missing/unknown enough that the plan cannot safely claim executable coverage.

Scenario Intelligence never marks a test PASS or FAIL.

## Duplicate control

Candidates receive a deterministic signature based on normalized kind, route, states, action intent and expected intent. Equivalent scenarios are merged rather than repeated.

The merge preserves:

- strongest deterministic evidence/confidence;
- highest priority;
- strictest readiness/runtime warning;
- union of source impact keys/evidence/targets.

Cross-state comparisons remain distinct because they test a relational invariant rather than one state independently.

## Generation budgets

`GenerationBudget` bounds:

- total scenarios;
- state variants per surface;
- cross-state groups.

When a budget truncates work, the plan records a coverage gap instead of silently pretending the omitted candidates were covered.

## Optional AI enrichment

AI is optional. `ScenarioEvidencePack` contains only bounded already-created scenarios and their evidence.

AI may improve:

- title wording;
- human explanation;
- a non-authoritative priority hint;
- confidence/readiness only in a more conservative direction.

AI may not:

- create scenarios;
- add affected routes/components/states;
- invent selectors, credentials, test data or API responses;
- increase deterministic confidence;
- promote runtime/manual coverage to `ready`;
- remove runtime-discovery requirements.

Unknown scenario keys are ignored. Provider errors or malformed JSON leave the deterministic plan unchanged.

## Persistence and CLI

Scenario Plans are saved outside the target repository using `JsonScenarioPlanStore`.

Default conceptual local store:

```text
~/.qgate/scenario-intelligence
```

CLI:

```text
qgate-scenario-intelligence generate \
  --knowledge <project-knowledge.json> \
  --impact <impact-report.json>
```

Use `--json` for structured output and `--store` to override the plan store location.

The analyzed target repository remains read-only.

## Local API

Local authenticated read-only endpoints:

```text
GET /api/v1/scenario-intelligence/plans
GET /api/v1/scenario-intelligence/latest
GET /api/v1/scenario-intelligence/plans/{key}
```

The store can be overridden with `SUITEST_SCENARIO_INTELLIGENCE_DIR`. Server mode returns 404. The browser cannot submit arbitrary filesystem paths to these endpoints.

## Dashboard

`/scenarios` shows:

- prioritized scenarios;
- READY/runtime/manual status;
- routes and states;
- preconditions;
- ordered actions and expected outcomes;
- reason/confidence/evidence counts;
- cross-state comparison groups;
- coverage gaps.

The dashboard reads persisted plans only; generation remains a controlled local operation.

## Testing

V1 tests cover:

- fingerprint mismatch fail-closed behavior;
- route/state scenario generation;
- runtime-discovery handling;
- scenario budgets;
- persistence and human-readable report;
- real Project Intelligence → Impact Analysis → Scenario Intelligence frontend fixture;
- AI guardrails/fallback;
- local authenticated API behavior;
- web populated/empty states.

Final branch verification also runs Ruff, mypy, web typecheck/build, affected suites, CLI smoke tests, route-tree generation and dashboard visual smoke.

## Important limitations

Scenario Intelligence V1 intentionally does not:

- prove actual browser reachability;
- discover selectors;
- create credentials or project-specific seed data;
- execute Suitest/Playwright;
- decide final QA status;
- use QA history;
- encode marketplace-specific business rules.

Those boundaries keep this phase reviewable and make the next execution phase explicit: **turn READY scenarios into real browser runs, collect evidence, and preserve unverified important scenarios as manual/runtime work instead of false PASSes.**
