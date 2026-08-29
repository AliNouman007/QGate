# QGate — Goal, Scope & Progress Tracker

This file is the single source of truth for QGate development progress and current product direction.

## Primary Goal

Build QGate as a local, developer-owned AI QA Gate that can understand a supplied software project, discover meaningful states and scenarios, execute evidence-backed tests, learn from confirmed QA findings, and return one of three outcomes:

- PASS
- BLOCK
- MANUAL REVIEW REQUIRED

QGate is not meant to become another generic AI code reviewer. It should reason about how software can actually behave and verify important behavior with deterministic/runtime evidence wherever possible.

## Core Product Direction

Use Suitest as the execution/platform foundation and add QGate-specific intelligence on top.

Core flow:

Project source
→ Project Intelligence ✅
→ Impact Analysis ✅
→ Scenario Intelligence ✅
→ Browser Execution & Evidence ✅
→ QA Memory ✅
→ Final Gate ✅

QGate V1 Core Pipeline: COMPLETE

Supported source adapters should eventually include:

- GitHub repositories
- extracted ZIP projects
- local project folders

The core must remain general-purpose. Domain-specific knowledge may later be added as optional profiles/adapters, but no specific marketplace or product domain should be hard-coded into the Project Intelligence core.

## Important Rules — Do Not Drift

- Follow `AGENTS.md` before making code changes.
- Keep QGate general-purpose unless a domain-specific extension is explicitly approved.
- Do not rebuild capabilities Suitest already provides unless there is a strong documented reason.
- Prefer real code/runtime/browser evidence over LLM guesses.
- The LLM is a reasoning layer, not the source of truth.
- Source of truth = code + static analysis + runtime browser + DOM/CSS/network/console evidence + QA memory.
- If an important scenario was not verified, QGate must not silently return PASS.
- QGate V1 detects and reports; it should not automatically fix the user's production code.
- Keep QGate isolated from the target repository. Do not inject QGate dependencies/config into the target project unless explicitly approved.
- Keep changes small, testable, documented, and traceable.
- Prefer the smallest correct solution; avoid unnecessary wrappers, abstraction layers, or function-on-function designs.
- Every behavioral code change needs appropriate tests.
- Every meaningful feature change must update the relevant documentation.
- Every AI implementation task must report files changed, per-file change summary, reason, tests, documentation updated, branch, commit SHA, and any unrelated changes.

## Existing Foundation — Completed

- [x] Evaluated Suitest as the base platform.
- [x] Verified Suitest can run Playwright-based E2E tests.
- [x] Verified Suitest can capture screenshots/video/logs/evidence.
- [x] Verified hidden runtime bug detection in the To-Do experiment.
- [x] Created private GitHub repository: `AliNouman007/QGate`.
- [x] Imported the Suitest source into QGate.
- [x] Preserved upstream license/notice files.
- [x] Added local authentication bypass for local development.
- [x] Auth bypass is opt-in via `SUITEST_LOCAL_AUTH_BYPASS`.
- [x] Auth bypass is restricted to local mode.
- [x] Verified bypass mode works.
- [x] Verified normal login mode still works.
- [x] Merged auth bypass into `main`.
- [x] Added `AGENTS.md` as the mandatory QGate engineering/AI-agent rulebook.
- [x] Added `docs/README.md` as the documentation index and update policy.
- [x] Made documentation maintenance mandatory for meaningful code changes.

## Phase 1 — Project Intelligence ✅ V1 COMPLETE

### Goal

Build a reliable, scalable structural and behavioral map of any supplied codebase without overwhelming the system on large projects.

Project Intelligence converts source code into structured, evidence-backed project knowledge rather than one large prose summary.

### Status

**Project Intelligence V1 was merged to `main` through PR #1.**

Merge commit:

`22f8dab8d35aaabda6996427fe4fee8cbd2039a7`

The final feature branch was locally verified before merge with:

- Project Intelligence tests: PASS
- provider-backed semantic tests: PASS
- local Project Intelligence API tests: PASS
- Project Map web tests: PASS
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- affected/root tests: PASS
- Next/React/TypeScript smoke test: PASS
- false Next.js positive test: PASS
- incremental/manifest invalidation test: PASS
- Project Map visual smoke: PASS

### Agreed architecture principles

- [x] General-purpose core; no marketplace-specific assumptions.
- [x] Hybrid analysis: deterministic/static analysis for facts, AI for semantic classification/grouping/prioritization.
- [x] Hierarchical/bounded scanning so large projects do not require unrestricted AI context.
- [x] Incremental re-analysis so unchanged project files can be reused.
- [x] Evidence and confidence attached to semantic/project-state claims.
- [x] Unknown/unresolved states represented instead of guessed.
- [x] Technical guards are separated from behaviorally meaningful conditions.
- [x] Project knowledge persists outside the target repository.
- [x] AI receives bounded evidence packs, never an unrestricted whole-repository dump.
- [x] AI cannot replace deterministic evidence or raise confidence above supporting evidence.
- [x] Safe deterministic fallback remains available when AI is absent or returns invalid output.

### V1 implemented capabilities

#### Source ingestion

- [x] Source adapter contract.
- [x] Local project-folder analysis.
- [x] ZIP project analysis with safe temporary extraction.
- [x] Adapter design remains extensible for GitHub or other transports.

#### Fast project index

- [x] Language/tooling detection.
- [x] Bounded file/folder inventory with ignore rules.
- [x] Likely routes, components/modules, tests, config, services, state and source roles.
- [x] File/size/depth analysis budgets.
- [x] Source fingerprints and per-file hashes.

#### Structural graph

- [x] Common Python and JS/TS import extraction.
- [x] Internal dependency graph.
- [x] Shared/reused module detection.
- [x] Evidence-backed relationships.
- [x] React component/hook/context/provider signals.
- [x] Next.js App Router route understanding.
- [x] Next.js Pages Router route understanding.
- [x] Dynamic Next.js route segments such as `[id]`, `[...slug]`, and `[[...slug]]`.
- [x] TypeScript interface/type/enum symbol extraction.
- [x] `use client` / `use server` boundary detection.
- [x] Common Next.js runtime/navigation API signals.
- [x] Package-manifest-backed framework detection to reduce false positives.

#### Behavioral extraction

- [x] Conditional/meaningful behavior signals.
- [x] Auth/permission-related conditions.
- [x] Feature-flag signals.
- [x] Loading/error/empty states where statically visible.
- [x] Browser storage/session/cookie-related signals where statically visible.
- [x] Responsive/breakpoint-related signals where statically visible.
- [x] Technical guard vs meaningful behavior classification.
- [x] Evidence and confidence preserved for extracted behavior.

#### Semantic classification

- [x] Deterministic bounded `EvidencePack` contract.
- [x] Rich semantic state kinds, labels, explanations, confidence, and runtime-verification flags.
- [x] Deterministic heuristic fallback for zero-LLM operation.
- [x] Optional provider-backed semantic enrichment through the existing Suitest `LLMProvider` abstraction.
- [x] Provider failures/malformed output safely fall back to deterministic classification.
- [x] Runtime-dependent or uncertain conclusions remain marked for verification.

#### Project Knowledge Store

- [x] Structured `ProjectKnowledge` schema.
- [x] Project summary, per-file facts, routes, symbols, dependency graph, semantic states, evidence, confidence and coverage gaps.
- [x] Analyzer/schema version and source fingerprint tracking.
- [x] JSON persistence in QGate-owned storage outside target repositories.
- [x] Stable stored-project keys and latest/list/detail reads.
- [x] Incremental unchanged-file reuse.
- [x] Framework/package-manifest changes invalidate relevant stale frontend interpretation.

#### Human-readable / dashboard Project Map

- [x] Human-readable CLI Project Map.
- [x] Local read-only Project Intelligence API.
- [x] Dashboard `/project-map` route.
- [x] Project Map shows languages/frameworks, routes, components, semantic states, reused modules, runtime-verification warnings and coverage gaps.
- [x] Sidebar navigation to Project Map.
- [x] Local API preserves normal authentication and does not accept arbitrary browser-supplied filesystem paths.
- [x] API behavior documented in `docs/API.md`.
- [x] Project Intelligence architecture/business workflow documented in `docs/PROJECT_INTELLIGENCE.md`.

### V1 validation completed

- [x] Fixture validation: routes/components/import graph.
- [x] Fixture validation: meaningful condition vs technical guard.
- [x] Fixture validation: reuse/dependency detection.
- [x] React/Next.js/TypeScript fixture and CLI smoke validation.
- [x] False Next.js positive regression validation.
- [x] Incremental changed-file validation.
- [x] Manifest/framework invalidation validation.
- [x] API + dashboard Project Map local smoke validation.

### Known limitations / later hardening

These do **not** block Project Intelligence V1 completion, but should be improved when they become valuable to later QGate phases:

- [ ] Native GitHub network/auth source adapter; for now a repository can be materialized locally and analyzed through the existing source contract.
- [ ] Full AST/compiler-level frontend parsing where regex/static extraction becomes insufficient.
- [ ] TypeScript path-alias resolution such as `@/` in the dependency graph.
- [ ] More complete dynamic import/metaprogramming/generated-route understanding.
- [ ] Large real-world repository benchmark and performance tuning beyond bounded fixture/local validation.
- [ ] Richer dashboard drill-down/graph visualization if Impact Analysis needs it.

## Phase 2 — Impact Analysis ✅ V1 COMPLETE

### Goal

Given a code change or PR diff, determine realistic blast radius and relevant states by reusing the merged `ProjectKnowledge` produced by Project Intelligence.

### Status

**Impact Analysis V1 was merged to `main` through PR #2.**

Merge commit:

`d9830ca22b7b96365b9b55a62ef05aab42be07c6`

The final feature branch was locally verified before merge with:

- Impact Analysis core unit tests: PASS (8 passed)
- AI Impact semantic tests: PASS (2 passed)
- local Impact Analysis API tests: PASS (3 passed)
- Web Impact dashboard tests: PASS (2 passed)
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- root/affected tests: PASS (397 web passed, 13 python passed)
- local Git ref comparison smoke test: PASS
- patch/diff parsing smoke test: PASS
- false positive exclusion: PASS
- traversal bounds & cycle safety: PASS
- AI evidence-pack guardrails & fallback: PASS
- Impact dashboard visual smoke: PASS

### V1 implemented capabilities

- [x] Define a structured ChangeSet / Impact Report contract.
- [x] Read changed files and changed lines from a local Git diff or supplied PR/diff source.
- [x] Map changed files/symbols into existing ProjectKnowledge.
- [x] Classify change type: UI, CSS, state, API, auth, pricing/business logic, routing, shared component, etc.
- [x] Trace direct dependencies.
- [x] Trace reverse dependencies and shared-component blast radius.
- [x] Identify affected routes/flows.
- [x] Identify relevant behavioral/semantic states.
- [x] Distinguish direct evidence from inferred impact.
- [x] Attach evidence/reason/confidence for every claimed impact.
- [x] Mark unresolved impact as unknown rather than guessing.
- [x] Produce a structured Impact Report that Scenario Intelligence can consume.
- [x] Add a concise developer-facing Impact view/report.
- [x] Add unit/integration tests and maintain `docs/IMPACT_ANALYSIS.md` as implementation begins.

## Phase 3 — Scenario Intelligence ✅ V1 COMPLETE

### Goal

Turn project knowledge + impact report into high-value, prioritized, evidence-backed QA test scenarios.

### Status

**Scenario Intelligence V1 was merged to `main` through PR #3.**

Merge commit:

`bfba67a68a24678b1cac3a59317abfeb156ce80b`

The final feature branch was locally verified before merge with:

- Scenario Intelligence core unit tests: PASS (7 passed)
- AI Scenario semantic tests: PASS (2 passed)
- local Scenario Intelligence API tests: PASS (3 passed)
- Web Scenario dashboard tests: PASS (2 passed)
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- root/affected tests: PASS (397 web passed, 12 python passed)
- CLI generate & JSON mode smoke: PASS
- fingerprint mismatch fail-closed check: PASS
- unrelated route exclusion: PASS
- state expansion budget bounds: PASS
- cross-state comparison generation: PASS
- scenario deduplication: PASS
- readiness guardrails: PASS
- AI evidence-pack guardrails & fallback: PASS
- Scenario dashboard visual smoke: PASS

### V1 implemented capabilities

- [x] Define a structured `ScenarioPlan` / candidate scenario contract.
- [x] Require matching source identity and fingerprint between ProjectKnowledge and ImpactReport (fail-closed).
- [x] Generate evidence-backed state variants and negative states without Cartesian explosion.
- [x] Generate cross-state comparisons when UI/state-sensitive code changes affect multiple related states.
- [x] Order scenarios by deterministic priority (P0–P3).
- [x] Distinguish automation readiness (`ready`, `runtime_discovery_required`, `manual_only`, `blocked_by_gap`).
- [x] Exclude unrelated routes and components.
- [x] Deduplicate equivalent candidate scenarios.
- [x] Bound generation via generation budgets and record coverage gaps.
- [x] Optional provider-backed AI enrichment with strict evidence-pack guardrails.
- [x] Save scenario plans in QGate-owned storage outside target repositories.
- [x] Human-readable CLI scenario plan view and `--json` mode.
- [x] Local read-only Scenario Intelligence API endpoints.
- [x] Dashboard `/scenarios` view with priority, readiness, step previews, cross-state groups and coverage gaps.

## Phase 4 — Browser Execution & Evidence ✅ V1 COMPLETE

### Goal

Execute READY scenarios in real browser (Chromium/Playwright), capture deterministic evidence, and classify runtime failures without misreporting environment or setup issues as product bugs.

### Status

**Browser Execution & Evidence V1 was merged to `main` through PR #4.**

Merge commit:

`5db20774c927e6355570fb43eca23b8edbd8d79b`

The final feature branch was locally verified before merge with:

- Browser Execution core unit tests: PASS (12 passed)
- Real Chromium integration tests: PASS
- Local Browser Execution API tests: PASS (3 passed)
- Web Execution dashboard tests: PASS (2 passed)
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- root/affected tests: PASS (8 web passed, 39 python passed)
- assertion regression classification: PASS
- environment failure classification: PASS
- fail-closed preconditions: PASS
- unsupported step fail-closed: PASS
- target resolution ambiguity handling: PASS
- evidence capture (DOM, CSS, console, network, screenshots): PASS
- header & secret redaction: PASS
- bounded retry policy (0/1): PASS
- CLI run & JSON mode smoke: PASS
- Execution dashboard visual smoke: PASS

### V1 implemented capabilities

- [x] Define structured `ExecutionRequest`, `ExecutionReport`, and `StepExecution` contracts.
- [x] Scenario compiler converting `ScenarioPlan` steps into executable `OperationKind` steps.
- [x] Target resolution using semantic role/label/test_id/text/selector metadata with fail-closed ambiguity checks.
- [x] Provision real Chromium browser via Suitest lifecycle (`ensure_browser`).
- [x] Capture per-step evidence: DOM snapshots, computed CSS, bounding box, console logs, network events, screenshots.
- [x] Redact sensitive credentials, auth headers, cookies, passwords, tokens, API keys, and card details before persistence.
- [x] Classify failure categories: `assertion_failure`, `navigation_failure`, `target_resolution_failure`, `environment_failure`, etc.
- [x] Enforce bounded retry policy (at most 1 retry for transient infra/browser errors; no retry on assertion failure).
- [x] Save execution reports outside target repository (`SUITEST_BROWSER_EXECUTION_DIR`).
- [x] CLI `qgate-browser-execution run` command with `--scenario-plan`, `--scenario`, `--priority`, and `--json`.
- [x] Local read-only Browser Execution API endpoints (`/api/v1/browser-execution/*`).
- [x] Web dashboard `/execution` view with step previews, failure categories, evidence artifacts, and coverage gaps.

## Phase 5 — QA Memory ✅ V1 COMPLETE

### Goal

Accumulate confirmed human QA findings and regression rules, deduplicate occurrences, enforce explicit human review gates, and provide deterministic recall for Scenario Intelligence planning.

### Status

**QA Memory V1 was merged to `main` through PR #5.**

Merge commit:

`009492c1784b1d68255ee4af5b586e9f385384d3`

The final feature branch was locally verified before merge with:

- QA Memory core unit tests: PASS (12 passed)
- End-to-end memory flow test: PASS
- Local QA Memory API tests: PASS (3 passed)
- Web QA Memory dashboard tests: PASS (3 passed)
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- root/affected tests: PASS (11 web passed, 54 python passed)
- candidate → human confirm/reject gate: PASS
- confirmed memory + regression rule creation: PASS
- rejected candidate trusted recall exclusion: PASS
- dedupe/occurrence history accumulation: PASS
- supersede/deactivate/reactivate lifecycle: PASS
- deterministic recall engine & ranking: PASS
- fingerprint fail-closed check: PASS
- recall budget bounds & truncation gaps: PASS
- Scenario Intelligence regression hint adapter: PASS
- CLI smoke (`add-human`, `ingest-execution`, `list`, `confirm`, `reject`, `recall`): PASS
- QA Memory dashboard visual smoke: PASS

### V1 implemented capabilities

- [x] Conservative automatic candidate extraction (verified `FAILED` + `ASSERTION_FAILURE` only).
- [x] Exclude environment/browser/setup/target-resolution failures from automatic regression candidates.
- [x] Human review lifecycle (`PENDING` → `CONFIRMED` or `REJECTED`).
- [x] Authenticated user id audit actor for candidate confirmation and rejection.
- [x] Confirmed memory creation with structured `RegressionRule`.
- [x] Exclude rejected candidates from trusted recall.
- [x] Candidate deduplication and occurrence history accumulation.
- [x] Confirmed memory lifecycle (`ACTIVE`, `SUPERSEDED`, `INACTIVE`) with deactivate and reactivate controls.
- [x] Deterministic recall engine ranking by scope (symbol, component, route, state) and impact level.
- [x] Fail-closed source identity and fingerprint check between ProjectKnowledge and ImpactReport.
- [x] Recall budget bounds and coverage gap reporting.
- [x] Scenario Intelligence hint adapter converting recalled rules into `RegressionScenarioHint` objects.
- [x] Save QA memory store outside target repository (`SUITEST_QA_MEMORY_DIR`).
- [x] Human-readable CLI `qgate-qa-memory` commands and `--json` support.
- [x] Local authenticated QA Memory API endpoints (`/api/v1/qa-memory/*`).
- [x] Dashboard `/qa-memory` view with candidate review actions, active memories, rules, and inactive history.

## Phase 6 — Final Gate ✅ V1 COMPLETE

### Goal

Produce a strict, evidence-backed decision (PASS, BLOCK, or MANUAL REVIEW REQUIRED) by synthesizing Project Intelligence, Impact Analysis, Scenario Intelligence, Browser Execution, and QA Memory artifacts.

### Status

**Final Gate V1 was merged to `main` through PR #6.**

Merge commit:

`5761688cd399f45106ec2ddfbc00b88c3457c7d5`

The final feature branch was locally verified before merge with:

- Final Gate core unit + judge + integration tests: PASS (9 passed)
- Local Final Gate API tests: PASS (3 passed)
- Web Final Gate dashboard tests: PASS (4 passed)
- Ruff: PASS
- mypy: PASS
- web typecheck/build: PASS
- python compileall: PASS
- root/affected tests: PASS (15 web passed, 66 python passed)
- strict verdict generation (PASS | BLOCK | MANUAL REVIEW REQUIRED): PASS
- input integrity / fingerprint fail-closed checks: PASS
- importance-aware required coverage policy (P0/P1/P2/P3): PASS
- verified product assertion failure → BLOCK: PASS
- environment/setup/browser/test gaps → MANUAL REVIEW REQUIRED: PASS
- conflicting evidence handling → MANUAL REVIEW REQUIRED: PASS
- zero required coverage fail-closed handling → MANUAL REVIEW REQUIRED: PASS
- confirmed historical regression obligations: PASS
- QA Memory non-blocker rule (memory alone does not create a current product block): PASS
- deterministic verdict authority & non-authoritative bounded AI explanation: PASS
- GateReport persistence outside target repository (`SUITEST_FINAL_GATE_DIR`): PASS
- CLI smoke (`evaluate`, `show`, `list`): PASS
- authenticated local API endpoints (`/api/v1/final-gate/*`): PASS
- Final Gate web dashboard `/gate` view: PASS

### V1 implemented capabilities

- [x] Deterministic-first decision engine returning `PASS`, `BLOCK`, or `MANUAL_REVIEW_REQUIRED`.
- [x] Input integrity verification across ProjectKnowledge, ImpactReport, ScenarioPlan, ExecutionReport, and MemoryRecallResult.
- [x] Fail-closed behavior on stale, mismatched, or corrupted input chains.
- [x] Importance-aware coverage policy promoting P0/P1 and impacted/recalled P2 scenarios to required status.
- [x] Fail-closed handling for zero required evaluable coverage.
- [x] Classification of verified product assertion failures as `BLOCK`.
- [x] Classification of environment, setup, browser, timeout, and infrastructure gaps as `MANUAL_REVIEW_REQUIRED`.
- [x] Conflict detection for required scenarios with simultaneous verified PASS and FAIL evidence.
- [x] Historical regression obligation tracking from QA Memory hints without reimplementing memory relevance.
- [x] Enforcement that historical memory alone never creates a current product block without current verified product evidence.
- [x] Bounded, optional AI explanation provider (`GateEvidencePack`) that cannot alter deterministic verdict, findings, or confidence.
- [x] GateReport persistence outside target repository (`SUITEST_FINAL_GATE_DIR`).
- [x] Human-readable CLI `qgate-final-gate` evaluation and inspection commands with `--json` support.
- [x] Local authenticated Final Gate API endpoints (`/api/v1/final-gate/*`).
- [x] Web dashboard `/gate` view showing verdict, blocking issues, required coverage, manual gaps, historical risks, and decision trace.

## Suitest Capabilities We Intend to Keep

- [x] Web dashboard
- [x] API/backend foundation
- [x] Runner/execution layer
- [x] Playwright integration
- [x] MCP layer
- [x] Evidence capture
- [x] Test/run management
- [x] Existing AI/provider abstraction where useful
- [x] Local development support

## Things to Review Later — Not Current Priority

These may be removed, disabled, or simplified only after QGate core works:

- [ ] Jira integration
- [ ] Linear integration
- [ ] Slack integration
- [ ] Kubernetes/infra testing modules
- [ ] Mobile/Appium-related capability if irrelevant
- [ ] Enterprise/multi-team features not needed for local V1
- [ ] Upstream release/publishing automation not needed for QGate
- [ ] Unnecessary branding and Suitest-specific UX

Do not remove these just for cleanliness before the core QGate flow is working.

## Testing Strategy

QGate should use multiple testing levels where they provide value:

- Unit tests for isolated parsing, graph, classification, and transformation logic.
- Integration tests for module/database/API interaction.
- E2E tests with Playwright for real user flows.
- Runtime DOM/computed CSS evidence for UI issues.
- Screenshot/visual evidence where useful.
- Console/network evidence where relevant.
- Regression tests for confirmed defects that could recur.

## Documentation Strategy

Documentation is a product requirement, not cleanup work.

- `AGENTS.md` = mandatory engineering and AI-agent rules.
- `docs/README.md` = documentation index and maintenance policy.
- `docs/PROJECT_INTELLIGENCE.md` = maintained Project Intelligence technical/business documentation.
- Each next major QGate subsystem receives a dedicated maintained document when implementation begins.
- Documentation must explain technical architecture and user/business workflow.
- Relevant documentation must be updated in the same feature branch whenever code behavior/contracts change.
- `QGATE_PROGRESS.md` must be updated after every meaningful merged feature.

## Current Next Step

**Run a real-world end-to-end QGate V1 validation on an actual code change before starting V1 hardening or new major features.**

## Definition of QGate V1 Success

QGate V1 is successful when, for a real code change, it can:

- [x] 1. Understand the affected code area.
- [x] 2. Identify realistic impacted states.
- [x] 3. Generate relevant test scenarios.
- [x] 4. Execute the automatable scenarios in a real browser.
- [x] 5. Collect evidence.
- [x] 6. Distinguish product bugs from test/environment failures.
- [x] 7. Use relevant historical QA knowledge.
- [x] 8. Return PASS, BLOCK, or MANUAL REVIEW REQUIRED with reasons/evidence.

## Progress Update Rule

After every meaningful merged feature:

1. Update this file.
2. Check completed items.
3. Add any newly discovered requirement.
4. Record major architectural decisions if they affect future work.
5. Update `Current Next Step` so development stays focused.
6. Update relevant documentation according to `docs/README.md`.

If a proposed task does not clearly support this roadmap, stop and question whether it belongs in QGate before implementing it.
