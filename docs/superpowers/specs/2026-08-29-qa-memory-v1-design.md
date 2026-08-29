# QA Memory V1 Design

## Purpose

QA Memory V1 gives QGate durable, project-specific learning without allowing unverified automation output to become permanent truth.

It implements a two-stage trust model:

`ExecutionReport / Defect / Human QA input`
→ `MemoryCandidate`
→ human confirm/reject
→ `ConfirmedMemory`
→ optional `RegressionRule`
→ deterministic recall against future `ProjectKnowledge + ImpactReport`
→ bounded memory context back into Scenario Intelligence.

QA Memory is not a defect tracker replacement and is not the Final Gate. Existing Suitest defects remain occurrence records; QA Memory stores reusable learning derived from confirmed occurrences.

## Product principles

1. Automated findings are candidates, never permanent truth by default.
2. Human confirmation is required before a candidate can influence future QA as trusted memory.
3. Rejected findings must not reappear as regression truth.
4. Existing Suitest `Defect` remains the issue/occurrence object; QA Memory links to it instead of duplicating it.
5. Memories must remain project-scoped in V1.
6. Every memory must retain provenance and evidence references.
7. Recall is deterministic-first and bounded; weak semantic similarity must not overpower concrete route/component/state matches.
8. AI is optional enrichment only and cannot invent historical facts, promote rejected/unconfirmed candidates, or raise confidence above evidence.
9. Historical records are superseded/deactivated, not silently deleted from audit history.
10. Target repositories remain read-only; memory persists in QGate-owned storage.
11. V1 remains general-purpose and frontend/browser-oriented, with no marketplace-specific hardcoding.
12. QA Memory does not decide PASS/BLOCK/MANUAL REVIEW REQUIRED; Final Gate remains Phase 6.

## Scope

QA Memory V1 is one feature PR and includes:

- structured contracts for memory candidates, confirmed memories, regression rules, recall results and audit events;
- candidate creation from Browser Execution findings;
- optional linkage to existing Suitest `Defect`, run/test-case identifiers and evidence references;
- human confirmation/rejection workflow;
- explicit supersede/deactivate lifecycle for confirmed memories;
- stable signatures/deduplication for repeated occurrences of the same underlying learning;
- deterministic recall against `ProjectKnowledge + ImpactReport`;
- bounded optional AI ranking/explanation guardrails;
- an adapter that exposes recalled regression knowledge to Scenario Intelligence without directly mutating existing plans;
- QGate-owned persistence;
- CLI for candidate ingestion, review state changes and recall;
- authenticated local API for reads and explicit review actions;
- `/qa-memory` dashboard with candidate queue and confirmed-memory views;
- unit/integration/API/web tests;
- documentation.

## Non-goals

V1 does not include:

- automatic confirmation of product bugs;
- automatic permanent memory creation from every failed browser execution;
- final QA gate decisions;
- production-code fixes;
- automatic mutation of the target repository;
- global cross-project learning;
- generic crowd-sourced QA knowledge;
- embedding/vector database dependency as a requirement;
- unrestricted whole-history LLM prompts;
- automatic deletion of historical decisions;
- automatic creation of Suitest defects when one does not already exist;
- autonomous promotion of a memory into an executable browser test without Scenario Intelligence.

## Existing Suitest relationship

Suitest `Defect` already models one bug occurrence and can link to a test case, run, requirement, severity, component, diagnosis kind and confidence.

QA Memory therefore uses:

- `Defect` = occurrence / issue-management truth;
- `MemoryCandidate` = proposed reusable learning;
- `ConfirmedMemory` = human-approved historical QA knowledge;
- `RegressionRule` = structured reusable expectation derived from confirmed memory.

A defect may produce zero or more memory candidates. A confirmed memory may retain a defect id, execution run id, scenario key and evidence references. QA Memory must not duplicate the full Defect record.

## Trust lifecycle

### Candidate status

- `PENDING` — proposed memory awaiting human review;
- `CONFIRMED` — candidate accepted and linked to a confirmed memory;
- `REJECTED` — candidate explicitly rejected and excluded from trusted recall.

Candidates are append-only historical records except for review status and review metadata.

### Confirmed memory status

- `ACTIVE` — eligible for future recall;
- `SUPERSEDED` — historical memory replaced by a newer memory/rule;
- `INACTIVE` — intentionally disabled from recall while audit history remains.

### Confirmation rules

A candidate can become trusted only through an explicit human review action.

Confirmation records at minimum:

- reviewer identity/reference;
- confirmation timestamp;
- optional review note;
- resulting confirmed memory key;
- evidence/source linkage.

Rejection records reviewer, timestamp and optional reason.

## Core data contracts

### `MemoryCandidate`

Minimum fields:

- stable candidate key;
- project source id;
- project fingerprint at discovery time;
- title;
- proposed invariant/expected behavior;
- candidate kind;
- severity/risk hint;
- affected routes;
- affected components/symbols/targets;
- relevant state labels;
- source scenario key;
- source execution report/run id;
- source defect id when available;
- source impact keys;
- evidence references;
- candidate confidence;
- status;
- created_at;
- reviewed_at/reviewer/review note where applicable;
- dedupe signature.

### Candidate kinds

Small V1 set:

- `ASSERTION_REGRESSION`
- `VISUAL_LAYOUT_REGRESSION`
- `STATE_BEHAVIOR_REGRESSION`
- `NAVIGATION_REGRESSION`
- `CONSOLE_RUNTIME_REGRESSION`
- `NETWORK_BEHAVIOR_REGRESSION`
- `HUMAN_REPORTED`
- `OTHER`

Environment/browser/setup failures must not become product-regression candidates automatically.

### `ConfirmedMemory`

Minimum fields:

- stable memory key;
- project source id;
- title;
- invariant/expected behavior;
- memory scope (`PROJECT_SPECIFIC` in V1);
- severity;
- routes;
- components/symbols/targets;
- states;
- originating candidate keys;
- source defect/run/scenario references;
- evidence references;
- confidence bounded by confirmed source evidence;
- status;
- confirmed_at / confirmed_by;
- superseded_by when applicable;
- tags;
- stable semantic signature.

### `RegressionRule`

A structured derivative of a confirmed memory.

Minimum fields:

- stable rule key;
- source memory key;
- project source id;
- rule title;
- target routes/components/symbols;
- relevant states/preconditions;
- expected invariant;
- suggested scenario objective;
- priority/severity hint;
- active flag;
- evidence references.

A rule is planning input, not executable Playwright code.

### `MemoryRecallResult`

Minimum fields:

- project source id;
- project fingerprint;
- impact change source id;
- generated_at;
- matched memories;
- matched regression rules;
- score/reason per match;
- evidence/source memory keys;
- recall coverage gaps;
- bounded result count.

## Candidate extraction from Browser Execution

Candidate extraction is conservative.

Automatic candidate creation is allowed for strong application-facing evidence such as:

- `FAILED + ASSERTION_FAILURE` after intended state was reached;
- repeated deterministic layout/state assertion failure where Browser Execution marked the run verified;
- deterministic application console/network regression only when Scenario/Execution contracts clearly identify it as the behavior under test.

Do not auto-create product-regression candidates from:

- `EXECUTION_ERROR` caused by environment/browser/infrastructure;
- `UNVERIFIED` scenarios;
- state setup failures;
- ambiguous target resolution;
- unsupported test definitions;
- dead server/network infrastructure failures;
- manual-only/blocked scenarios.

Such records may remain source evidence for manual investigation but are not product QA memories by default.

## Human-reported candidates

V1 supports an explicit human-submitted candidate for findings discovered by human QA even when Browser Execution did not catch them.

Required human input must include at least:

- project source id;
- title;
- expected invariant;
- route/component/state targeting where known;
- optional evidence/source defect/run references.

Human-created candidate is still `PENDING` until explicitly confirmed unless the same authenticated review action intentionally creates-and-confirms in one audited operation. The audit record must make that action explicit.

## Deduplication

Repeated executions should not create dozens of equivalent memories.

Candidate dedupe signature should normalize evidence-backed identity from:

- project source id;
- candidate kind;
- normalized route/component/symbol targets;
- normalized state labels;
- normalized expected invariant;
- source scenario/regression identity where available.

If an equivalent candidate already exists:

- retain occurrence linkage/count/history;
- do not create a duplicate permanent memory;
- a previously rejected candidate may receive another occurrence, but rejection is not silently reversed;
- a confirmed equivalent candidate links to the existing confirmed memory.

## Supersede and deactivate

Confirmed memories are not hard-deleted during normal V1 use.

### Supersede

Used when expected behavior legitimately changes.

Example:

Old confirmed rule: `Checkout label must be You Pay`.

Product requirement later intentionally changes the label.

A reviewer creates/confirms the new memory and supersedes the old one. Old memory remains auditable but excluded from active recall.

### Deactivate

Used when memory should temporarily/permanently stop influencing QA but no replacement truth is being asserted.

All lifecycle changes record actor, timestamp and optional reason.

## Recall architecture

Inputs:

- current `ProjectKnowledge`;
- current `ImpactReport`;
- active confirmed memories and regression rules for the same project source id.

Recall is deterministic-first.

### Matching priority

1. same symbol/component + same relevant state;
2. same route/surface + same state;
3. same shared component/symbol without exact state match;
4. dependency/reverse-dependency relationship supported by current `ProjectKnowledge`;
5. same route/component family with supporting evidence;
6. bounded semantic text similarity only as a low-priority enrichment signal.

Rejected candidates, pending candidates, inactive memories and superseded memories are excluded from trusted recall.

### Recall score

Score components should be explicit and inspectable, for example:

- exact symbol/component match;
- route match;
- state match;
- current Impact level (`DIRECT > INDIRECT > POSSIBLE > UNKNOWN`);
- severity;
- recency as a minor tie-breaker only;
- evidence confidence.

No hidden AI-only relevance score may be the sole reason a memory is recalled.

## Bounded recall

Default V1 limits should prevent history explosion, for example:

- max recalled memories: 20;
- max recalled rules: 20;
- max evidence refs per recalled item: bounded;
- explicit `recall_truncated`/coverage gap when relevant matches exceed budget.

The exact constants can be configuration values, but behavior must remain deterministic and tested.

## Optional AI enrichment

AI may improve:

- concise labels/explanations;
- grouping of already-matched memories;
- ordering among deterministic near-ties;
- suggested scenario wording from an existing confirmed regression rule.

AI may not:

- recall pending/rejected memories as trusted history;
- create historical events that do not exist;
- invent a route/component/state absent from source memory/current project evidence;
- increase memory confidence above source evidence;
- activate/supersede/confirm memories;
- convert weak semantic similarity into an exact historical match;
- remove provenance/evidence;
- send unrestricted whole-memory history to a provider.

Provider failure/malformed output falls back to deterministic recall unchanged.

## Scenario Intelligence integration

QA Memory V1 must not create a second Scenario Intelligence engine.

It exposes a small adapter/input contract:

`MemoryRecallResult → recalled regression scenario hints`

A hint contains:

- source memory/rule key;
- scenario objective;
- affected route/component/state;
- expected invariant;
- priority/severity hint;
- evidence/provenance;
- runtime/manual constraints if known.

Scenario Intelligence may consume these hints in a future/current integration point to generate or prioritize regression scenarios.

Important rule: a recalled memory is a reason to test historical risk again, not evidence that the current code is already broken.

## Persistence

Use QGate-owned persistence outside the target repository.

V1 may use JSON-backed stores consistent with Project/Impact/Scenario/Execution packages unless repository conventions strongly favor a small local database layer during implementation.

Persistence must support:

- save/load candidate;
- list/filter candidates by status/project;
- confirm/reject mutation with audit metadata;
- save/load confirmed memory;
- supersede/deactivate mutation;
- list active memories;
- regression rule persistence;
- recall history/result persistence where useful;
- stable traversal-safe keys;
- deterministic serialization.

Do not put QGate memory files in the analyzed target repository.

## API

Local authenticated API follows existing QGate local-mode patterns.

Read endpoints conceptually include:

- list candidates;
- candidate detail;
- list confirmed memories;
- memory detail;
- latest/explicit recall result where useful.

Explicit mutation endpoints include only intentional human review/lifecycle actions:

- confirm candidate;
- reject candidate;
- supersede memory;
- deactivate/reactivate memory if V1 includes reactivation;
- optional create human candidate.

Rules:

- workspace authentication required;
- local mode only for QGate-owned memory store in V1;
- server mode hidden/404 following existing patterns where applicable;
- no arbitrary local filesystem path input;
- no arbitrary code/JavaScript execution;
- reviewer identity comes from authenticated context, not a free-form spoofable browser field where the existing auth model can provide it.

## CLI

Provide developer-facing commands conceptually like:

- `qgate-qa-memory ingest-execution --report <execution-report.json>`;
- `qgate-qa-memory candidates`;
- `qgate-qa-memory confirm <candidate-key>`;
- `qgate-qa-memory reject <candidate-key> --reason ...`;
- `qgate-qa-memory memories`;
- `qgate-qa-memory supersede <memory-key> --with <new-memory-key>`;
- `qgate-qa-memory recall --knowledge <knowledge.json> --impact <impact.json>`;
- `--json` where appropriate.

CLI review commands must require an explicit reviewer/audit identity in local CLI context if authenticated user context is unavailable.

## Dashboard

Add `/qa-memory` under Insights.

V1 dashboard shows:

### Candidate queue

- status;
- title/kind;
- severity/confidence;
- route/component/state scope;
- source execution/defect/scenario references;
- evidence summary;
- duplicate/occurrence count;
- confirm/reject actions;
- review reason/history.

### Confirmed memories

- active/superseded/inactive status;
- invariant;
- project scope;
- route/component/state targeting;
- severity/confidence;
- regression rule linkage;
- source candidate/defect/run;
- supersede/deactivate actions;
- recall relevance preview/history where practical.

UI must clearly distinguish `PENDING` candidate from trusted `ACTIVE` memory.

## Audit model

Every trust-changing action records an immutable audit event:

- candidate created;
- occurrence linked/deduped;
- candidate confirmed;
- candidate rejected;
- memory created;
- memory superseded;
- memory deactivated/reactivated if supported;
- regression rule created/updated from confirmed memory.

Minimum audit fields:

- event id;
- entity key/type;
- action;
- actor/reviewer;
- timestamp;
- reason/note;
- source entity key when applicable.

## Safety and privacy

QA Memory inherits Browser Execution redaction rules.

Do not persist raw secrets, authorization headers, passwords, payment data or unrestricted sensitive payloads into candidate/memory text.

Evidence references should point to bounded/redacted evidence rather than duplicating large raw artifacts.

Human notes should be treated as project-private data and never sent to an LLM unless included in a bounded approved enrichment pack.

## Failure behavior

- Store corruption/read failure must not silently return an empty trusted memory set when Final Gate depends on it; surface a recall/store gap.
- Project source mismatch fails closed.
- Missing current project fingerprint may still allow project-scoped historical lookup by explicit source id, but exact structural relevance must remain unknown until current ProjectKnowledge is available.
- Invalid lifecycle transition returns explicit error.
- Confirming an already rejected candidate requires an explicit audited reversal path if supported; otherwise V1 rejects the transition and requires a new reviewed candidate.
- Superseded/inactive memories are never returned as active regression truth.

## Testing strategy

### Candidate extraction

- verified `ASSERTION_FAILURE` creates a pending candidate;
- environment failure does not create a product-regression candidate;
- unverified/state-setup/target-resolution failures do not auto-create trusted product candidates;
- human candidate creation is pending by default;
- sensitive evidence remains redacted/referenced.

### Trust lifecycle

- pending → confirmed succeeds with reviewer audit;
- pending → rejected succeeds;
- rejected candidate excluded from recall;
- confirmed candidate creates/links exactly one confirmed memory;
- invalid transitions fail closed;
- superseded/inactive memory excluded from active recall;
- audit history preserved.

### Deduplication

- repeated same execution failure increments occurrence/linkage instead of duplicating memory;
- changed state/invariant produces separate signature when behavior is meaningfully different;
- rejected duplicate does not silently reactivate.

### Recall

Use fixture where confirmed memory targets a shared frontend component/state.

Verify:

- same component + same state ranks highest;
- same route relevant memory is recalled;
- unrelated `/admin`-style memory is excluded;
- indirect dependency relation ranks below exact match;
- pending/rejected/inactive/superseded memories never appear as trusted recall;
- recall budget truncation produces explicit gap;
- stable deterministic ordering.

### Scenario adapter

- confirmed recalled regression rule produces a structured scenario hint;
- provenance preserved;
- hint does not claim current failure;
- no raw Playwright code/selectors invented.

### AI guardrails

- bounded matched-memory packs only;
- no whole history dump;
- AI cannot activate/reject/confirm memory;
- cannot add nonexistent memory keys/routes/states;
- cannot raise confidence;
- provider failure preserves deterministic recall.

### Persistence/CLI/API/web

- save/load/list/latest/filter where applicable;
- traversal-safe keys;
- CLI ingestion/review/recall smoke;
- local authenticated API tests;
- server-mode hidden behavior if following current local QGate endpoint pattern;
- dashboard candidate/confirmed/empty-state tests;
- web typecheck/build;
- Ruff/mypy/root affected tests.

## V1 acceptance criteria

QA Memory V1 is complete when:

1. Browser Execution product assertion failures can create `PENDING` candidates without becoming trusted history.
2. Human reviewers can confirm or reject candidates with audit evidence.
3. Confirmed candidates create durable project-specific memories and optional regression rules.
4. Rejected candidates never influence trusted future recall.
5. Duplicate occurrences do not create duplicate permanent memories.
6. Memories can be superseded/deactivated without deleting history.
7. Future `ProjectKnowledge + ImpactReport` can deterministically recall relevant active memories/rules.
8. Unrelated memories are excluded and recall remains bounded.
9. Scenario Intelligence can receive provenance-rich regression hints without QA Memory generating Playwright code itself.
10. Existing Suitest Defect remains linked occurrence data rather than being duplicated.
11. CLI/API/dashboard expose the lifecycle clearly.
12. Tests prove false-positive protection, dedupe, recall relevance, AI guardrails and lifecycle safety.
13. No target-repository modification is required.
14. Final Gate remains a separate phase.

## Out of scope for later versions

- global cross-project learning;
- organization-wide generic QA rule promotion;
- semantic/vector index optimization for very large memory history;
- automatic memory decay based on time alone;
- auto-confirmation based on repeated executions;
- automatic requirement-change detection that supersedes old memories;
- rich graph visualization of historical regressions;
- direct Final Gate policy decisions.
