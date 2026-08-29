# Final Gate V1

Final Gate is QGate's strict final QA decision layer.

It consumes the already-produced QGate evidence chain:

`ProjectKnowledge -> ImpactReport -> ScenarioPlan -> ExecutionReport -> QA Memory recall -> GateReport`

and returns exactly one public verdict:

- `PASS`
- `BLOCK`
- `MANUAL_REVIEW_REQUIRED`

## Decision philosophy

Final Gate is deterministic-first. It does not ask an LLM to guess whether a change is safe.

- **BLOCK** means QGate has a relevant, verified product-facing failure with deterministic runtime evidence.
- **MANUAL_REVIEW_REQUIRED** means QGate cannot justify PASS because important evidence is missing, blocked, manual-only, conflicting, stale, or environment/setup dependent.
- **PASS** means the artifact chain is valid, all required important scenarios are verified, strongly relevant historical regression obligations are covered, and no blocking product failure remains.

A test that could not run is not automatically a product bug, but it also cannot silently become PASS.

## Required coverage policy

V1 uses importance-aware coverage rather than a simple pass percentage.

- P0: required.
- P1: required.
- P2: required when it covers direct current impact or a strongly matched confirmed historical regression.
- P3: optional by default unless historical/current evidence promotes it.

One missing P0/P1 cannot be hidden by many passing optional scenarios.

A meaningful change with zero required evaluable coverage returns `MANUAL_REVIEW_REQUIRED` rather than PASS.

## Product failures vs execution gaps

Final Gate reuses Browser Execution classifications.

A verified required `assertion_failure` can produce BLOCK because the browser evidence establishes that an expected product invariant was violated.

The following normally produce MANUAL for a required scenario instead of BLOCK:

- environment failure;
- browser failure;
- network infrastructure failure;
- state setup failure;
- target resolution failure;
- test definition error;
- unresolved timeout;
- unknown execution failure;
- manual-only/blocked/unverified execution.

Timeout alone is not proof that the product is slow or broken.

## Input integrity

Final Gate validates that ProjectKnowledge, ImpactReport, ScenarioPlan, ExecutionReport, and supplied QA Memory recall belong to the same project/change chain.

Project ids, project fingerprints, change-source ids, scenario-plan key, and execution run linkage are checked before the verdict is trusted.

A stale/mismatched chain returns `MANUAL_REVIEW_REQUIRED`. Final Gate does not trust a blocker from a mismatched chain because the evidence may belong to a different code state.

## QA Memory

Only active confirmed QA Memory that has already been recalled for the current impact can influence Final Gate.

Historical memory can:

- promote regression coverage to required;
- explain why a scenario matters;
- require manual review when a strongly relevant historical regression was not re-verified.

Historical memory cannot directly BLOCK the current change. A current BLOCK still requires current verified product evidence.

`RegressionScenarioHint` from the existing QA Memory adapter carries the recalled rule's route/state/invariant provenance so Final Gate can link historical risk to a concrete planned scenario without reimplementing memory relevance.

## Verdict precedence

For a valid artifact chain:

1. verified blocking product failure -> `BLOCK`;
2. otherwise any required uncertainty/gap -> `MANUAL_REVIEW_REQUIRED`;
3. otherwise all required coverage verified -> `PASS`.

BLOCK has precedence over simultaneous manual gaps because once a current verified blocker exists the developer already has a reason to stop. The report still records remaining manual gaps.

## GateReport

A GateReport includes:

- verdict and confidence;
- deterministic headline;
- blocking findings;
- manual-review findings;
- informational findings;
- required/optional coverage summary;
- per-scenario coverage items;
- strongly relevant historical regression risks;
- input-integrity findings;
- evidence references;
- inspectable decision trace;
- optional AI explanation stored separately from deterministic fields.

## AI role

AI is optional and non-authoritative.

It receives a bounded `GateEvidencePack` containing only the deterministic verdict, fired rules, concise findings, required coverage summaries, and historical-risk summaries.

AI may improve wording, group reasons, or produce a manual-review checklist. It cannot modify the deterministic verdict, erase gaps, downgrade blockers, invent evidence, or raise confidence.

If AI is unavailable or invalid, the deterministic GateReport remains unchanged.

## Persistence and CLI

Gate reports persist outside target repositories under:

`SUITEST_FINAL_GATE_DIR=~/.qgate/final-gate`

The local CLI is `qgate-final-gate`.

Example evaluation:

```text
qgate-final-gate evaluate \
  --project project.json \
  --impact impact.json \
  --scenario-plan scenarios.json \
  --scenario-plan-key <stored-key> \
  --execution execution.json \
  --memory-recall recall.json \
  --regression-hints hints.json
```

Use `--json` for structured output. The CLI may accept explicit local paths because it is a developer-local command. The web API does not expose arbitrary filesystem evaluation.

## Local API

Final Gate V1 exposes read-only authenticated local endpoints:

- `GET /api/v1/final-gate/reports`
- `GET /api/v1/final-gate/latest`
- `GET /api/v1/final-gate/reports/{key}`

Server mode hides this local report surface with 404, matching other QGate local intelligence modules.

## Dashboard

`/gate` leads with the final verdict and then shows:

1. why this verdict;
2. blocking product failures;
3. required scenario coverage;
4. manual-review items;
5. relevant confirmed QA Memory;
6. evidence/decision trace.

Environment/setup gaps must not be styled or described as verified product bugs.

## V1 scope limits

Final Gate V1 does not:

- edit production code;
- automatically fix failures;
- merge pull requests;
- bypass human QA policy;
- create new test scenarios that Scenario Intelligence never planned;
- reimplement Browser Execution failure classification;
- reimplement QA Memory relevance ranking.
