# Final Gate V1 Design

## Purpose

Final Gate V1 is the strict decision layer that converts the existing QGate evidence chain into one developer-facing outcome:

- `PASS`
- `BLOCK`
- `MANUAL_REVIEW_REQUIRED`

It consumes structured artifacts produced by the already-merged QGate subsystems:

`ProjectKnowledge + ImpactReport + ScenarioPlan + ExecutionReport + MemoryRecallResult`
→ input integrity
→ coverage evaluation
→ verified-failure evaluation
→ historical-risk evaluation
→ conflict/unknown evaluation
→ deterministic verdict
→ optional bounded AI explanation
→ `GateReport`.

Final Gate does not replace upstream analysis/execution. It judges their evidence conservatively and audibly.

## Approved decision philosophy

1. A verified, relevant, product-facing blocking failure produces `BLOCK`.
2. Important unverified/blocked/manual/conflicting coverage produces `MANUAL_REVIEW_REQUIRED`, not a false product bug.
3. `PASS` is allowed only when all required important coverage is sufficiently verified and there is no blocking verified product failure.
4. Missing evidence can never be converted into PASS by optimism or AI.
5. Environment/setup/browser/infrastructure failures are not product bugs unless independent product evidence proves otherwise.
6. Historical QA Memory is a reason to require regression coverage, not proof that the current change is broken.

## Architecture choice

Use a hybrid deterministic gate with optional bounded AI explanation.

The deterministic engine owns the verdict. AI may summarize/group/explain already-established evidence, but it cannot:

- upgrade `BLOCK` to `PASS`;
- upgrade `MANUAL_REVIEW_REQUIRED` to `PASS`;
- downgrade a verified blocker;
- erase required coverage gaps;
- invent evidence, routes, states, failures, or historical facts;
- raise confidence above deterministic evidence;
- reinterpret rejected/inactive/superseded QA Memory as trusted truth.

If AI is absent, fails, times out, or returns invalid output, the deterministic GateReport remains valid and unchanged.

## Inputs

Final Gate V1 consumes:

- `ProjectKnowledge`
- `ImpactReport`
- `ScenarioPlan`
- `ExecutionReport`
- optional `MemoryRecallResult`

A MemoryRecallResult may be absent when there are no relevant confirmed memories. Its absence must be explicit and must not be confused with a failed memory lookup.

## Input integrity / fail-closed rules

Before any verdict is evaluated, Final Gate validates the artifact chain.

At minimum:

- ProjectKnowledge source id must match ImpactReport project source id.
- ProjectKnowledge source fingerprint must match ImpactReport project fingerprint.
- ScenarioPlan source/project identity must match the ProjectKnowledge + ImpactReport chain.
- ExecutionReport scenario plan key must match the ScenarioPlan key used for the decision.
- ExecutionReport project source/fingerprint must match the same project chain.
- Impact change source id must match across ImpactReport, ScenarioPlan, and ExecutionReport where those fields exist.
- MemoryRecallResult, when supplied, must match the same project source/fingerprint and current impact change source.

Any stale/mismatched/incomplete artifact identity prevents PASS.

Default outcome for integrity failure:

`MANUAL_REVIEW_REQUIRED`

with structured reason `INPUT_INTEGRITY_GAP` or a more specific subtype.

A mismatched chain is not a product bug and therefore must not become BLOCK by itself.

## Core contracts

### `GateVerdict`

- `PASS`
- `BLOCK`
- `MANUAL_REVIEW_REQUIRED`

### `GateConfidence`

- `HIGH`
- `MEDIUM`
- `LOW`

Confidence describes confidence in the gate decision, not confidence that the product is bug-free.

A deterministic BLOCK backed by verified browser assertion evidence may be HIGH confidence.
A MANUAL decision caused by missing critical evidence may also be HIGH confidence as a decision to require manual review.

### `GateReasonKind`

V1 should include a small explicit set such as:

- `VERIFIED_PRODUCT_FAILURE`
- `REQUIRED_SCENARIO_UNVERIFIED`
- `REQUIRED_SCENARIO_BLOCKED`
- `REQUIRED_SCENARIO_MANUAL_ONLY`
- `ENVIRONMENT_OR_SETUP_GAP`
- `TARGET_RESOLUTION_GAP`
- `TEST_DEFINITION_GAP`
- `TIMEOUT_UNRESOLVED`
- `HISTORICAL_REGRESSION_UNVERIFIED`
- `CONFLICTING_EVIDENCE`
- `INPUT_INTEGRITY_GAP`
- `COVERAGE_TRUNCATED`
- `NO_REQUIRED_COVERAGE`
- `ALL_REQUIRED_COVERAGE_VERIFIED`

### `GateFinding`

Minimum fields:

- stable key
- kind
- severity/priority
- scenario key when applicable
- route/component/state context where available
- title
- reason
- verdict effect (`BLOCKING`, `MANUAL_REVIEW`, `INFORMATIONAL`)
- evidence references
- source execution run/scenario/step references
- source memory/rule references where applicable
- verified flag
- product_facing flag when applicable

### `CoverageItem`

Minimum fields:

- scenario key
- scenario priority
- required flag
- required_reason
- readiness
- execution status
- verified flag
- failure category
- historical regression linkage if any
- coverage outcome: `VERIFIED_PASS`, `VERIFIED_FAIL`, `UNVERIFIED`, `MANUAL`, `BLOCKED`, `OPTIONAL`
- evidence refs

### `CoverageSummary`

Importance-aware counts, not a single percentage:

- required_total
- required_verified_pass
- required_verified_fail
- required_unverified
- required_manual
- required_blocked
- optional_total
- optional_verified
- historical_required_total
- historical_required_verified
- truncated / coverage_gap flags

A percentage may be shown for convenience but must never drive the verdict by itself.

### `GateDecisionTrace`

Ordered inspectable rules that fired, for example:

1. input chain valid
2. scenario `checkout_wallet` marked required because P1 + direct impact
3. execution verified assertion failure
4. failure category is application assertion, not environment/setup
5. blocking rule fired
6. final verdict BLOCK

No hidden AI-only decision reason is permitted.

### `GateReport`

Minimum fields:

- stable report key
- schema/gate version
- generated_at
- project source id/fingerprint
- change source id
- scenario plan key
- execution run id
- verdict
- confidence
- headline / deterministic summary
- blocking findings
- manual review findings
- informational findings
- coverage summary
- coverage items
- historical risks
- input integrity findings
- evidence refs
- decision trace
- optional AI explanation metadata/output

## Required-scenario policy

Final Gate must not treat every scenario equally.

Default V1 policy:

- P0: required
- P1: required
- P2: required when directly impacted OR backed by a strongly matched active confirmed regression rule; otherwise optional by default
- P3: optional by default unless explicitly promoted by upstream scenario metadata/policy

Additional required conditions:

- a strongly matched active historical regression rule may promote a related scenario to required, at least P1-equivalent for gate coverage purposes;
- a scenario explicitly marked as critical/manual-required by upstream evidence may be required even if its numeric priority is lower;
- required status must be inspectable with a `required_reason`.

Final Gate must not silently invent a scenario that Scenario Intelligence never planned. If memory indicates an important regression risk but there is no matching planned/executed scenario, record `HISTORICAL_REGRESSION_UNVERIFIED` and require manual review rather than inventing execution evidence.

## Verified product-failure policy

A scenario failure can contribute to BLOCK only when all required conditions are met:

1. scenario is relevant to current impact/plan;
2. execution is verified;
3. evidence represents application/product behavior rather than an execution harness failure;
4. failure category/evidence supports the expected product invariant being violated;
5. scenario is required/blocking under policy, or an optional scenario reveals a sufficiently severe verified product defect according to configured severity policy.

Strong BLOCK examples:

- verified `ASSERTION_FAILURE` on required product invariant;
- verified navigation assertion where navigation behavior itself is the requirement;
- verified state/layout invariant failure represented as an assertion failure with deterministic DOM/CSS evidence.

Final Gate should reuse Browser Execution classification and evidence rather than creating a second generic failure-classification engine.

## Non-product failure policy

These normally prevent PASS for required scenarios but do not themselves prove a product bug:

- `ENVIRONMENT_FAILURE`
- `BROWSER_FAILURE`
- `NETWORK_INFRA_FAILURE`
- `STATE_SETUP_FAILURE`
- `TARGET_RESOLUTION_FAILURE`
- `TEST_DEFINITION_ERROR`
- unresolved `TIMEOUT`
- `UNKNOWN_EXECUTION_FAILURE`
- preclassified `UNVERIFIED`
- `SKIPPED_MANUAL`
- `BLOCKED`

For a required scenario these lead to `MANUAL_REVIEW_REQUIRED`, with the exact category preserved.

For optional P3-like scenarios they may be informational unless another rule promotes them to required.

## Timeout policy

Timeouts are ambiguous by default.

V1 default:

- timeout alone => manual review for required scenario;
- timeout becomes BLOCK only if the ExecutionReport already contains independent verified product evidence that clearly establishes the product invariant failure before/at timeout;
- Final Gate must not infer that a timeout means the product is slow/broken without such evidence.

## Coverage policy

PASS requires all required scenarios to reach an acceptable verified state.

Acceptable PASS coverage:

- required scenario executed and `PASSED` with verified=true;
- required historical regression coverage is represented by an appropriate planned scenario and verified PASS;
- no required scenario remains unverified/manual/blocked;
- no important ScenarioPlan/Execution coverage gap indicates omitted required work;
- no input mismatch/staleness exists.

A large number of optional passing scenarios can never compensate for one missing required P0/P1 scenario.

## ScenarioPlan coverage gaps

Scenario Intelligence coverage gaps must be evaluated, not ignored.

If a coverage gap directly affects required P0/P1 or required historical regression coverage, verdict cannot PASS.

Generation budget truncation affecting potentially required coverage produces `MANUAL_REVIEW_REQUIRED` with `COVERAGE_TRUNCATED`.

Weak/optional gaps may be informational if they cannot affect required coverage under deterministic evidence.

## Browser Execution coverage gaps

Execution coverage gaps are mapped back to scenario requirements.

Examples:

- required scenario unsupported by compiler => MANUAL
- required state setup unknown => MANUAL
- required scenario manual-only => MANUAL
- optional P3 unsupported => informational unless promoted

## QA Memory policy

Only active confirmed memories/rules present in `MemoryRecallResult` may influence the gate.

Pending/rejected candidates and inactive/superseded memories are not trusted gate inputs.

QA Memory can:

- promote regression coverage importance;
- explain why a related scenario is required;
- produce manual review when a strongly relevant historical regression was not re-verified;
- enrich evidence provenance.

QA Memory cannot:

- directly produce BLOCK merely because a bug happened historically;
- override a current verified PASS with historical suspicion alone;
- create a current defect without current evidence.

## Historical-risk matching

Use the already-produced MemoryRecallResult rather than implementing a second memory-relevance engine.

Final Gate evaluates recall strength/reason from that result.

Strongly matched active regression rule + current direct/indirect impact:

- related scenario should be required;
- if verified PASS: historical risk considered covered;
- if verified FAIL with product evidence: may BLOCK;
- if absent/unverified/manual: MANUAL REVIEW REQUIRED.

Weak informational recall does not automatically promote coverage.

## Conflict handling

Conflicting deterministic evidence prevents PASS when the conflict affects a required product invariant.

Examples:

- one required execution says PASS while another authoritative execution for same scenario/change says verified FAIL;
- ScenarioPlan/source identity disagrees with ExecutionReport identity;
- evidence refs indicate incompatible states with no resolved explanation.

V1 must represent conflict explicitly as `CONFLICTING_EVIDENCE` and return MANUAL unless one side is deterministically stale/invalid and can be excluded by input-integrity rules.

AI may summarize a conflict but may not resolve it by opinion.

## Verdict precedence

Final deterministic precedence:

### 1. BLOCK

Return BLOCK when at least one verified blocking product failure exists.

A real product blocker has precedence even if other scenarios are manual/unverified; the report should still list those gaps.

### 2. MANUAL_REVIEW_REQUIRED

When no BLOCK exists, return MANUAL if any required uncertainty/gap exists, including:

- required scenario unverified;
- required scenario manual-only/blocked;
- environment/setup/browser/target/test-definition issue prevented required verification;
- required historical regression unverified;
- required coverage truncated;
- conflicting evidence;
- input integrity mismatch;
- no sufficient required coverage to justify PASS.

### 3. PASS

Return PASS only when:

- input chain valid;
- there are no verified blocking product failures;
- all required scenarios are sufficiently verified PASS;
- all strongly relevant historical regression requirements are covered;
- no critical/manual/conflicting/integrity gap remains.

## No-required-coverage rule

Final Gate must not return PASS just because zero scenarios were considered required.

If a meaningful current change has no required evaluable coverage, return MANUAL with `NO_REQUIRED_COVERAGE` unless deterministic evidence proves the change is outside browser/product scope and upstream policy explicitly marks the gate as not applicable.

V1 may keep `not applicable` out of the public verdict enum; if so, such cases remain MANUAL unless a later design adds an explicit scoped-skip concept.

## Confidence policy

Confidence is deterministic and explainable.

Suggested rules:

- HIGH BLOCK: verified required assertion failure with strong browser evidence;
- HIGH MANUAL: definite missing required P0/P1 execution or definite input mismatch;
- MEDIUM MANUAL: unresolved timeout/conflict with partial evidence;
- HIGH PASS: all required scenarios verified, no material gaps, matching artifacts;
- MEDIUM PASS should generally be avoided in V1; if evidence is not sufficient for HIGH PASS, prefer MANUAL.

PASS should therefore usually be HIGH confidence in V1.

## AI evidence pack

Optional AI receives a bounded `GateEvidencePack` containing only:

- deterministic verdict;
- fired rule ids/reasons;
- concise required coverage items;
- concise blocking/manual findings;
- bounded evidence excerpts/refs;
- bounded historical risk summaries;
- conflict summaries.

Do not send unrestricted ProjectKnowledge, whole repo, full browser logs, or whole QA Memory history.

AI output may include:

- developer-facing explanation;
- grouped reasons;
- concise manual-review checklist;
- wording improvements.

AI output is stored separately from deterministic decision fields.

## Persistence

Persist GateReports in QGate-owned storage outside the target repository.

Suggested env:

`SUITEST_FINAL_GATE_DIR=~/.qgate/final-gate`

JSON-backed persistence is acceptable for V1, consistent with the existing QGate intelligence packages.

Required operations:

- save GateReport
- load by stable key
- list reports
- latest report
- filter/list by project source where useful
- traversal-safe keys
- deterministic serialization

## CLI

Add a local CLI such as `qgate-final-gate`.

Required capabilities:

- generate GateReport from explicit persisted artifact paths/keys;
- human-readable output;
- `--json` mode;
- optionally select explicit MemoryRecallResult;
- fail clearly on missing/mismatched artifacts;
- never discover arbitrary target paths through the web API.

Human-readable output should lead with the verdict and the minimal reasons needed to act.

Example:

`BLOCK — checkout_wallet violated expected invariant "You Pay" (verified assertion failure)`

or

`MANUAL REVIEW REQUIRED — P1 wallet regression scenario was not verified because state setup failed`.

## API

Local authenticated API follows existing QGate patterns.

Read-only dashboard endpoints are sufficient in V1 because verdict generation can remain CLI/service driven.

Conceptual endpoints:

- `GET /api/v1/final-gate/reports`
- `GET /api/v1/final-gate/latest`
- `GET /api/v1/final-gate/reports/{key}`

If an API generation endpoint is added, it must accept stable QGate artifact identifiers, not arbitrary filesystem paths, and must remain local-mode/authenticated.

Server mode may hide local Final Gate endpoints with 404, consistent with other QGate local intelligence surfaces.

## Dashboard

Add `/gate` under the QGate Insights navigation.

Primary screen goal: a developer should understand within seconds whether the change is ready to send onward and why.

Top verdict card:

- PASS
- BLOCK
- MANUAL REVIEW REQUIRED

Then concise sections:

1. Why this verdict
2. Blocking findings
3. Required scenario coverage
4. Manual review items
5. Relevant QA Memory / historical regressions
6. Evidence references
7. Decision trace

The screen must clearly distinguish:

- verified product failures;
- unverified/manual/environment gaps;
- historical risk;
- optional informational findings.

Do not render an environment failure as a red product-bug card.

## User workflow

Expected V1 flow:

1. Developer runs QGate against a change.
2. Existing phases produce ProjectKnowledge, ImpactReport, ScenarioPlan, ExecutionReport, and memory recall.
3. Final Gate validates artifact integrity.
4. Required coverage is determined.
5. Verified failures and gaps are classified.
6. Historical regression obligations are evaluated.
7. Deterministic verdict is produced.
8. Optional AI explanation is generated without altering verdict.
9. GateReport is persisted.
10. Developer sees PASS/BLOCK/MANUAL with evidence and knows whether to proceed to human QA.

## End-to-end acceptance examples

### Example A — verified checkout regression

Current impact: checkout summary directly changed.
Scenario: P1 logged-in + wallet.
Execution: verified assertion expected `You Pay`, actual `Total`.
Environment: healthy.

Expected Final Gate:

`BLOCK`

Reason: verified relevant product invariant failure.

### Example B — browser/setup failure

Required P1 checkout scenario cannot execute because browser/environment fails.

Expected Final Gate:

`MANUAL_REVIEW_REQUIRED`

Reason: required scenario not verified due environment/setup; no product bug claim.

### Example C — historical regression not re-tested

Memory recall strongly matches an active confirmed wallet regression rule.
Current change directly impacts checkout.
No matching required regression scenario was executed.

Expected Final Gate:

`MANUAL_REVIEW_REQUIRED`

Historical memory does not directly BLOCK; missing re-verification prevents PASS.

### Example D — complete clean evidence

All P0/P1 and promoted historical regression scenarios verified PASS.
No required gaps, no input mismatch, no product failure.

Expected Final Gate:

`PASS` with HIGH confidence.

### Example E — optional low-value gap

All required P0/P1 coverage verified PASS.
One unrelated optional P3 scenario is unverified due unsupported setup.

Expected Final Gate:

`PASS` if deterministic evidence shows the optional gap cannot affect required coverage; report it informationally.

## Test strategy

V1 requires unit/integration/API/web coverage for at least:

- exact artifact identity matching;
- fingerprint/change-source fail-closed behavior;
- required-scenario policy P0/P1/P2/P3;
- verified assertion failure => BLOCK;
- environment/browser/setup failure => MANUAL, not BLOCK;
- required unverified/manual/blocked => MANUAL;
- optional P3 gap does not automatically prevent PASS;
- zero required coverage cannot silently PASS;
- memory recall promotes required regression coverage;
- historical memory alone cannot BLOCK;
- rejected/inactive/superseded memory cannot influence GateReport through trusted recall input;
- strong historical risk unverified => MANUAL;
- all required verified PASS => PASS;
- conflicting evidence => MANUAL;
- BLOCK precedence over simultaneous manual gaps;
- coverage truncation affecting required work => MANUAL;
- bounded AI cannot change deterministic verdict;
- AI provider failure leaves deterministic report unchanged;
- store/CLI/API/dashboard behavior;
- local/server-mode endpoint behavior;
- visual smoke for `/gate`.

## Non-goals

Final Gate V1 does not:

- modify/fix production code;
- merge PRs;
- approve deployment automatically;
- replace human QA for manually required states;
- create new browser scenarios independently of Scenario Intelligence;
- reimplement QA Memory relevance;
- reimplement Browser Execution failure classification;
- treat historical defects as current failures without current evidence;
- use an LLM as the source of truth;
- change the public verdict enum beyond PASS/BLOCK/MANUAL REVIEW REQUIRED.

## V1 completion criteria

Final Gate V1 is complete when QGate can take one consistent artifact chain for a real code change and deterministically produce a persisted, explainable PASS/BLOCK/MANUAL REVIEW REQUIRED verdict where:

- a verified relevant product failure blocks;
- critical missing verification requires manual review rather than false PASS/BLOCK;
- environment/setup failures are not misreported as product bugs;
- confirmed historical QA knowledge increases regression coverage obligations without becoming false current evidence;
- PASS requires sufficient verified evidence for every required important scenario;
- the decision is inspectable through CLI/API/dashboard with traceable evidence.
