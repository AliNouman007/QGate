# Scenario Intelligence V1 Design

## Purpose

Scenario Intelligence V1 converts the merged `ProjectKnowledge` and `ImpactReport` contracts into a structured, prioritized QA `ScenarioPlan` that tells QGate what should be tested next. It does not execute browsers, write production code, or make the final PASS/BLOCK/MANUAL decision.

## Product workflow

`ProjectKnowledge + ImpactReport`
→ derive relevant impacted surfaces and states
→ expand evidence-backed state variants
→ generate scenario candidates
→ generate cross-state comparisons where useful
→ score priority/reachability
→ remove duplicates/redundancy
→ assess automation readiness
→ optionally enrich bounded scenario evidence with AI
→ persist structured `ScenarioPlan`
→ expose CLI/API/dashboard views
→ feed future Suitest/Playwright execution.

## Core principles

1. `ImpactReport` is the primary source of truth for what changed and what may be affected.
2. `ProjectKnowledge` supplies known routes, symbols, behaviors, semantic states, dependencies, evidence and coverage gaps.
3. Scenario generation is deterministic-first. AI is optional and bounded.
4. Every generated scenario must explain why it exists and link back to source impact/evidence.
5. Scenario Intelligence must prefer realistic, reachable, high-value states over theoretical combinatorial expansion.
6. Unknown or runtime-dependent states are preserved as runtime discovery/manual-review requirements instead of guessed away.
7. Scenario Intelligence outputs structured QA scenarios, not raw Playwright code.
8. Existing Suitest test-case/execution contracts should be reused where practical instead of building a second execution engine.
9. Duplicate and near-duplicate scenarios must be collapsed before handoff to execution.
10. Domain-specific profiles are future extensions; the V1 core remains general-purpose.

## Scope

Scenario Intelligence V1 is one complete feature PR and includes:

- structured `ScenarioPlan`, `Scenario`, `ScenarioStep`, state/target/evidence contracts;
- deterministic generation from `ImpactReport` and `ProjectKnowledge`;
- route/component/state targeting;
- positive, negative/state-edge, and regression-oriented scenarios where evidence supports them;
- cross-state comparison scenarios for UI/state-sensitive changes;
- scenario priority and reachability scoring;
- duplicate and redundant scenario collapsing;
- automation readiness assessment;
- explicit runtime-discovery/manual-only marking;
- evidence, confidence and source-impact traceability;
- bounded optional AI enrichment through the existing provider abstraction;
- persisted QGate-owned Scenario Plans;
- human-readable CLI output;
- local authenticated read-only API;
- `/scenarios` dashboard view;
- unit/integration/API/web tests;
- `docs/SCENARIO_INTELLIGENCE.md` and required API/docs/config updates.

## Inputs

### Required

- one `ImpactReport`;
- matching `ProjectKnowledge`.

The generator must validate that the project source id/fingerprint represented by the `ImpactReport` matches the supplied `ProjectKnowledge`. A mismatch must fail clearly or mark the plan stale; it must not silently mix knowledge from different snapshots.

### Optional

- generation budget/limits;
- optional AI provider;
- later domain/profile hints through an extension point, not hard-coded core logic.

## Structured output

### `ScenarioPlan`

At minimum:

- schema/analyzer versions;
- generated timestamp;
- project source id and fingerprint;
- impact change source id;
- scenario counts by priority/readiness/type;
- ordered scenarios;
- cross-state groups;
- runtime-discovery/manual requirements;
- coverage gaps and warnings;
- generation limits used.

### `Scenario`

At minimum:

- stable key/id;
- title;
- scenario kind;
- priority;
- confidence;
- target route(s)/component/module/state where known;
- preconditions;
- relevant state keys/labels;
- ordered steps;
- expected assertions/outcomes;
- reason/rationale;
- source impact keys;
- evidence;
- automation readiness;
- `needs_runtime_discovery`;
- `manual_reason` where automation is not currently safe;
- optional cross-state group key;
- optional AI explanation/priority hint constrained by deterministic guardrails.

### `ScenarioStep`

The structured step should align closely with Suitest's execution shape:

- action;
- expected;
- optional route/target context;
- optional data/state hint;
- target kind, normally `FE_WEB` for the current frontend-focused V1;
- optional recommended MCP provider only when known from existing routing contracts;
- no invented selectors or raw Playwright code in Scenario Intelligence V1.

## Scenario kinds

V1 should support a small explicit set such as:

- `SMOKE` — confirm directly impacted surface still renders/functions;
- `STATE_VARIANT` — exercise a meaningful affected state;
- `NEGATIVE_STATE` — exercise absent/denied/error/empty or equivalent evidence-backed state;
- `CROSS_STATE_COMPARISON` — compare behavior/visual structure across related states;
- `ROUTE_REGRESSION` — verify affected dependent route/surface;
- `RUNTIME_DISCOVERY` — structured placeholder for a scenario that cannot yet be reached/proven statically.

Do not create arbitrary scenario taxonomies that execution does not need.

## Deterministic candidate generation

The generator starts from Impact Analysis outputs.

### Direct impacts

High-value candidates should be created for directly changed routes/components/states when enough information exists to identify a test surface.

Examples:

- directly changed route → smoke scenario;
- directly changed semantic state → state-variant scenario;
- directly changed UI/styling component reused on several routes → representative route scenarios plus shared/cross-state coverage.

### Indirect impacts

Reverse-dependent routes/components should generate regression scenarios when the deterministic dependency path is present. These should normally rank below direct impacts unless the shared blast radius is broad.

### Possible/unknown impacts

Do not automatically create fully executable scenarios from weak evidence. Produce runtime-discovery/manual requirements or low-confidence candidates with explicit reasons.

### Affected states

State scenarios should be generated from Impact Analysis affected-state items plus matching ProjectKnowledge semantic/behavior evidence. State expansion must remain bounded.

Examples of meaningful state pairs where evidence exists:

- authenticated / unauthenticated;
- permission allowed / denied;
- feature flag on / off;
- data present / empty;
- loading / loaded;
- error / success;
- storage/session/cookie present / absent;
- responsive/breakpoint variants;
- item has value / item missing value.

The engine must not generate every theoretical Cartesian product of state dimensions.

## State expansion rules

State expansion is conservative and evidence-backed.

Priority order:

1. states directly impacted by changed evidence;
2. states explicitly listed in `ImpactReport.affected_states`;
3. meaningful counterpart states strongly implied by the same behavior fact/state family;
4. dependent-surface states only when a deterministic dependency path exists;
5. runtime-dependent state candidates marked for discovery rather than assumed reachable.

A configurable budget limits total state expansions per affected surface and total scenarios per plan.

## Cross-state comparison scenarios

Cross-state comparison is important for UI/regression problems that only appear when two valid states differ unexpectedly.

Generate a cross-state comparison when:

- the change category includes UI/styling/state/responsive/shared behavior; and
- two related evidence-backed states exist for the same surface; and
- comparison produces distinct value beyond separate smoke scenarios.

Examples:

- rating present vs rating absent card layout;
- logged-in wallet vs guest checkout summary;
- feature flag control vs variation;
- mobile vs desktop layout.

The scenario must describe the comparison goal structurally (alignment, visibility, expected label/value relationship, stable layout) without inventing pixel values/selectors unless the project evidence provides them.

## Prioritization

Scenario priority is deterministic-first and separate from confidence.

Suggested V1 priority enum: `P0`, `P1`, `P2`, `P3`.

Scoring factors:

- direct impact > indirect > possible;
- high-confidence evidence > medium > low;
- changed state/route/component match;
- shared/reused component breadth;
- number of affected routes;
- auth/permission/feature/state/API categories may increase relevance but must not be treated as business severity without evidence;
- runtime-only/theoretical candidates rank lower for automated execution but remain visible;
- duplicate coverage lowers incremental priority.

V1 should not claim financial/business severity unless a later profile or evidence explicitly supplies it.

## Reachability and automation readiness

Use a small readiness enum:

- `READY` — route/preconditions/actions/assertions are concrete enough for the execution layer to attempt;
- `RUNTIME_DISCOVERY_REQUIRED` — scenario matters but QGate lacks enough static information to reach or assert it safely;
- `MANUAL_ONLY` — scenario cannot currently be represented safely as browser automation;
- `BLOCKED_BY_GAP` — required project/impact evidence is missing or stale.

Readiness is not execution result. Scenario Intelligence does not mark PASS/FAIL.

A scenario should be `READY` only when it has:

- at least one target surface/route or a concrete entry action;
- explicit preconditions when state setup matters;
- at least one action;
- at least one expected outcome/assertion;
- sufficient deterministic evidence linking it to the impact.

## Suitest compatibility

Scenario Intelligence should output steps that can later be adapted into Suitest `TestCaseCreate`/`StepCreate` semantics:

- `name/title` ← scenario title;
- `preconditions` ← scenario preconditions;
- `priority` ← scenario priority;
- `steps[].action` ← structured action;
- `steps[].expected` ← expected outcome;
- `targetKind` ← frontend V1 defaults to `FE_WEB`;
- no raw `code` is required at Scenario Intelligence stage;
- execution-layer/provider routing remains owned by Suitest/QGate execution, not this generator.

Do not persist Scenario Intelligence output directly as production TestCase rows in V1. Persist a separate Scenario Plan first so review/dedup/prioritization remains reversible.

## Duplicate/redundancy control

Duplicate control is mandatory.

Create a deterministic scenario signature using normalized:

- target surface/route;
- state set;
- scenario kind;
- action intent;
- expected intent;
- source impact family.

When candidates collide:

- preserve the strongest evidence/confidence;
- merge source impact keys/evidence;
- keep the higher priority;
- preserve runtime/manual warnings;
- avoid producing multiple scenarios that test the same state on the same surface with equivalent assertions.

Cross-state comparison scenarios remain separate from their component state scenarios because they test a relational invariant.

## AI enrichment boundary

AI is optional and receives bounded `ScenarioEvidencePack` objects, never unrestricted ProjectKnowledge/ImpactReport dumps.

A pack may contain:

- one scenario candidate or a small related group;
- deterministic target/state/impact facts;
- bounded evidence excerpts;
- current priority/readiness;
- explicit allowed output schema.

AI may:

- improve title/rationale wording;
- suggest clearer human-facing action/expected wording grounded in provided facts;
- suggest grouping labels;
- suggest a lower/equal priority hint;
- recommend runtime discovery.

AI may not:

- invent new affected routes/components/states not present in evidence;
- invent selectors, credentials, API responses or user data;
- remove deterministic evidence;
- raise confidence above deterministic support;
- change `RUNTIME_DISCOVERY_REQUIRED`/`MANUAL_ONLY` to `READY` without deterministic proof;
- create unsupported scenario candidates.

Malformed/provider failure falls back unchanged to deterministic output.

## Persistence

Scenario Plans live in QGate-owned storage outside target repositories.

Each plan should include:

- project source id/fingerprint;
- impact change source id;
- deterministic plan identity/hash;
- generated timestamp/version;
- stale detection metadata.

Support save/load/list/latest by stable key similar to Project Intelligence and Impact Analysis stores.

## CLI

Provide concise local developer commands to generate from persisted inputs, for example conceptually:

`qgate-scenario-intelligence generate --knowledge <knowledge.json> --impact <impact.json>`

Outputs:

- human-readable prioritized Scenario Plan;
- JSON mode for later automation/integration;
- optional output/store path.

CLI errors clearly on missing/mismatched/stale-enough inputs rather than guessing.

## Local API and dashboard

Expose read-only local-mode endpoints through normal QGate workspace authentication, following Project Map/Impact patterns:

- list persisted Scenario Plans;
- latest Scenario Plan;
- detail by stable key.

Server mode remains hidden/404 unless later explicitly supported.

Browser UI must not accept arbitrary filesystem paths.

Dashboard `/scenarios` should answer quickly:

- what should be tested;
- priority order;
- route/component/state target;
- why scenario exists;
- actions and expected outcomes;
- confidence/evidence;
- READY vs runtime-discovery/manual status;
- cross-state groups;
- coverage gaps/unknowns.

## Error handling and safety

- Missing ProjectKnowledge → explicit failure/blocked plan.
- Missing ImpactReport → explicit failure.
- Project fingerprint mismatch → fail or mark blocked/stale; never mix silently.
- No meaningful impacted surface → produce a plan with coverage gap/manual requirement, not synthetic scenarios.
- Unknown route but meaningful impacted state → runtime-discovery candidate, not a fake URL.
- Unsupported/dynamic state reachability → runtime-discovery requirement.
- Generation budget reached → coverage gap stating omitted candidate count/reason.
- AI provider failure/malformed output → deterministic plan unchanged.
- Target repository remains read-only.

## Testing strategy

### Unit tests

- impact-to-scenario candidate generation;
- direct vs indirect prioritization;
- route/component targeting;
- semantic/behavior state expansion;
- no Cartesian state explosion;
- cross-state comparison generation;
- duplicate signature/collapse;
- priority scoring;
- READY/runtime/manual readiness rules;
- mismatch/stale input behavior;
- generation budgets/gaps;
- AI evidence/route/state/confidence/readiness guardrails and fallback.

### Integration fixture

Build a React/Next/TypeScript fixture through the real pipeline:

1. generate ProjectKnowledge;
2. baseline Git commit;
3. change a shared component with two meaningful states;
4. generate ImpactReport;
5. generate ScenarioPlan;
6. verify direct scenario targets changed component/surface;
7. verify dependent affected routes receive regression scenarios;
8. verify two meaningful states create bounded state variants;
9. verify UI/state pair creates cross-state comparison;
10. verify unrelated route receives no scenario;
11. verify duplicates are collapsed;
12. verify plan persists/reloads unchanged.

Additional fixtures should cover auth/permission or feature-flag states, styling-only change, runtime-only/unknown state, and broad shared-component reuse under scenario budgets.

### API/web tests

- empty Scenario Plan state;
- list/latest/detail reads;
- local-only behavior;
- authentication preserved;
- server-mode hidden behavior;
- dashboard renders priority, targets, steps, evidence, readiness, cross-state groups and gaps;
- production web typecheck/build.

## Success criteria

Scenario Intelligence V1 is complete when a realistic frontend code change can produce a structured evidence-backed plan that correctly:

1. generates scenarios only for relevant impacted surfaces/states;
2. prioritizes direct/high-confidence scenarios above indirect/possible ones;
3. represents meaningful state variants without combinatorial explosion;
4. creates useful cross-state comparisons for state-sensitive UI changes;
5. excludes unrelated routes/components;
6. collapses redundant scenarios;
7. marks execution-ready scenarios separately from runtime/manual discovery;
8. supplies action + expected outcome + preconditions suitable for later Suitest/Playwright adaptation;
9. links every scenario to impact/evidence/confidence;
10. persists a stable ScenarioPlan contract that the execution phase can consume.

## Non-goals

- writing raw Playwright/Selenium code;
- executing browsers/tests;
- generating or storing production credentials/test data;
- deciding PASS/BLOCK/MANUAL REVIEW REQUIRED;
- classifying runtime failures;
- QA Memory/history learning;
- automatic production-code fixes;
- domain-specific marketplace rules in the core;
- unrestricted whole-repository or whole-impact LLM prompting.
