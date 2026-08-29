# QA Memory V1

QA Memory gives QGate durable, project-specific regression knowledge without allowing automated failures to become permanent truth by themselves.

## Trust model

`ExecutionReport / human finding`
→ `MemoryCandidate (PENDING)`
→ explicit human review
→ `CONFIRMED` or `REJECTED`
→ confirmed candidate creates/links an `ACTIVE ConfirmedMemory`
→ optional `RegressionRule`
→ deterministic recall against future `ProjectKnowledge + ImpactReport`
→ structured regression scenario hints.

Pending and rejected candidates are never trusted recall inputs.

## Relationship to Suitest Defects

Suitest `Defect` remains the occurrence/issue-management object. QA Memory may store a `source_defect_id` but does not duplicate the Defect record. A confirmed memory captures reusable QA learning such as an invariant, affected surface/state, provenance and evidence.

## Candidate extraction

Automatic extraction is conservative. V1 automatically proposes a memory candidate only when Browser Execution reached the intended application state and returned a verified `FAILED` result with `ASSERTION_FAILURE`.

The following do not automatically become product-regression candidates:

- `EXECUTION_ERROR`
- environment/browser/infrastructure failures
- `UNVERIFIED`
- state setup failures
- target resolution ambiguity
- unsupported test definitions
- dead server/network infrastructure failures.

## Human review

Trust-changing actions are explicit and audited:

- confirm candidate
- reject candidate
- supersede memory with another confirmed memory
- deactivate memory
- reactivate an inactive memory.

The authenticated API user's id is used as the reviewer/actor. Clients cannot submit an arbitrary reviewer identity.

Rejected candidates remain historical records. A repeated equivalent occurrence can be linked to the same candidate, but rejection is not silently reversed.

## Dedupe

Candidate signatures normalize project, candidate kind, route/component/symbol/state scope, invariant and source scenario identity. Repeated equivalent failures accumulate occurrence references instead of producing many duplicate candidates or memories.

Confirmed memories also have a stable semantic signature. Confirming an equivalent candidate links the candidate to the existing active memory where appropriate.

## Confirmed memory lifecycle

- `ACTIVE`: eligible for trusted recall.
- `SUPERSEDED`: replaced by a newer confirmed memory and excluded from recall.
- `INACTIVE`: intentionally disabled and excluded from recall.

Normal lifecycle operations never hard-delete history.

## Regression rules

A confirmed memory may produce a structured RegressionRule containing:

- project id
- source memory key
- routes/components/symbols
- relevant states/preconditions
- expected invariant
- scenario objective
- severity hint
- evidence references.

Rules are planning inputs. They do not contain raw Playwright code and are not proof that the current code is broken.

## Deterministic recall

Recall requires matching `ProjectKnowledge` and `ImpactReport` source id/fingerprint.

Ranking is inspectable and deterministic-first. Stronger signals include:

1. same symbol/component + state
2. same route + state
3. same symbol/component
4. same route
5. dependency-supported relationship
6. current direct/indirect impact
7. severity/confidence as small ranking bonuses.

Weak matches below the threshold are excluded. Recall is bounded and reports truncation gaps when configured limits are exceeded.

Pending/rejected candidates and inactive/superseded memories do not participate in trusted recall.

## Scenario Intelligence integration

`MemoryRecallResult` can be converted to bounded `RegressionScenarioHint` records. A hint says that a historical risk should be tested again. It does **not** say that the current change already contains the bug.

Scenario Intelligence remains responsible for turning planning hints into concrete scenarios. Browser Execution remains responsible for runtime verification.

## Persistence

Default QGate-owned storage:

`~/.qgate/qa-memory`

Override with:

`SUITEST_QA_MEMORY_DIR`

The target repository is never used as memory persistence.

## CLI

The `qgate-qa-memory` command supports:

- `ingest-execution --report <execution-report.json>`
- `add-human --project-source-id ... --title ... --invariant ...`
- `list --kind candidates|memories|rules [--json]`
- `confirm <candidate-key> --reviewer ...`
- `reject <candidate-key> --reviewer ...`
- `recall --knowledge <project-knowledge.json> --impact <impact-report.json> [--json]`

CLI reviewer arguments are explicit audit actors for local developer use. The HTTP API uses the authenticated user id instead.

## Local API

QA Memory API is local-mode only, authenticated and workspace-scoped.

Read surfaces:

- `GET /api/v1/qa-memory/candidates`
- `GET /api/v1/qa-memory/candidates/{key}`
- `GET /api/v1/qa-memory/memories`
- `GET /api/v1/qa-memory/memories/{key}`
- `GET /api/v1/qa-memory/rules`

Intentional review/lifecycle actions:

- `POST /api/v1/qa-memory/candidates/{key}/confirm`
- `POST /api/v1/qa-memory/candidates/{key}/reject`
- `POST /api/v1/qa-memory/memories/{key}/supersede`
- `POST /api/v1/qa-memory/memories/{key}/deactivate`
- `POST /api/v1/qa-memory/memories/{key}/reactivate`

There is no API for arbitrary code execution or target-repository mutation.

## Dashboard

`/qa-memory` separates:

- pending review candidates
- confirmed trusted memory
- rejected history
- inactive/superseded memory.

The UI deliberately labels pending findings as proposed learning rather than confirmed bugs.

## V1 limitations

QA Memory V1 does not:

- make Final Gate PASS/BLOCK/MANUAL REVIEW REQUIRED decisions
- automatically confirm failures
- learn globally across projects
- require vector embeddings
- automatically create Suitest defects
- directly execute regression rules
- automatically edit production code.
