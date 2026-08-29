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
→ Project Intelligence
→ Impact Analysis
→ Scenario Intelligence
→ Suitest / Playwright execution
→ Evidence collection
→ QA Memory
→ Final Gate

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

## Phase 1 — Project Intelligence

### Goal

Build a reliable, scalable structural and behavioral map of any supplied codebase without overwhelming the system on large projects.

Project Intelligence should convert source code into structured project knowledge rather than one large prose summary.

### Agreed architecture principles

- [x] General-purpose core; no marketplace-specific assumptions.
- [x] Hybrid analysis: deterministic/static analysis for facts, AI for semantic classification/grouping/prioritization.
- [x] Hierarchical scanning: lightweight whole-project indexing before targeted deep analysis.
- [x] Incremental re-analysis so large projects do not require a full deep scan after every change.
- [x] Evidence and confidence attached to AI-derived/project-state claims where possible.
- [x] Unknown/unresolved states must be represented instead of guessed.
- [x] Do not treat every technical `if`/guard as a meaningful QA state.
- [x] Persist project knowledge outside the target repository.

### Planned V1 capabilities

#### Source ingestion

- [ ] Define a source adapter contract.
- [ ] Support analysis from a local/extracted project path first.
- [ ] Keep adapters extensible for GitHub repositories and extracted ZIPs without coupling the analysis engine to one transport.

#### Stage 1 — Fast project index

- [ ] Detect languages/frameworks/tooling.
- [ ] Build file/folder inventory with sensible ignore rules.
- [ ] Identify likely source roots, test roots, config files, routes, components/modules, services, and state-management areas.
- [ ] Enforce file/size/depth budgets so large repositories remain bounded.

#### Stage 2 — Structural graph

- [ ] Scan routes/pages where supported.
- [ ] Scan components/modules/symbols where supported.
- [ ] Build import/dependency graph.
- [ ] Detect shared/reused modules and components.
- [ ] Record code evidence for discovered relationships.

#### Stage 3 — Behavioral extraction

- [ ] Detect conditional rendering and meaningful state branches.
- [ ] Detect auth/permission-related conditions.
- [ ] Detect feature flags.
- [ ] Detect loading/error/empty states where statically visible.
- [ ] Detect important props/state/API dependencies.
- [ ] Detect relevant cookies/localStorage/session usage.
- [ ] Detect responsive/breakpoint logic where useful.
- [ ] Separate technical guards from behaviorally meaningful states.

#### Stage 4 — Semantic classification

- [ ] Define a deterministic fact/evidence package for AI input.
- [ ] Use AI only on bounded evidence packs, not whole-repo dumps.
- [ ] Group low-level conditions into meaningful behavioral states when evidence supports it.
- [ ] Record confidence and evidence references.
- [ ] Mark uncertain results as UNKNOWN / NEEDS RUNTIME VERIFICATION.

#### Stage 5 — Project Knowledge Store

- [ ] Define structured Project Intelligence output schema.
- [ ] Persist project summary, route/module graph, dependency graph, state catalog, evidence, confidence, and analysis metadata outside the target repo.
- [ ] Track analysis version/source fingerprint.
- [ ] Support incremental invalidation/re-analysis of changed files and affected graph regions.

#### Human-readable output

- [ ] Produce a concise Project Map for developers.
- [ ] Allow drill-down from area/module/state to supporting code evidence.
- [ ] Report coverage gaps and unsupported constructs instead of silently omitting them.

### Project Intelligence V1 validation

Validate first on small fixture projects, then on a larger real-world frontend repository.

- [ ] Small fixture: routes/components/import graph.
- [ ] Small fixture: meaningful condition vs technical guard.
- [ ] Small fixture: reuse/dependency detection.
- [ ] Large-project test: bounded analysis completes without loading the entire repo into an LLM context.
- [ ] Incremental test: changing one file re-analyzes only the required project region.

## Phase 2 — Impact Analysis

Goal: given a code change or PR diff, determine realistic blast radius and relevant states using Project Intelligence knowledge.

Planned capabilities:

- [ ] Read changed files/lines.
- [ ] Classify change type: UI, CSS, state, API, auth, pricing/business logic, routing, shared component, etc.
- [ ] Trace direct dependencies.
- [ ] Trace indirect/reused component impact.
- [ ] Identify affected routes/flows.
- [ ] Identify affected state combinations.
- [ ] Attach evidence/reason for each claimed impact.
- [ ] Produce structured Impact Report.

## Phase 3 — Scenario Intelligence

Goal: turn project knowledge + impact report into high-value QA scenarios.

Planned capabilities:

- [ ] Generate realistic state variants from code evidence.
- [ ] Prioritize likely/reachable states over purely theoretical states.
- [ ] Generate E2E scenarios for Suitest/Playwright.
- [ ] Generate cross-state comparison scenarios where useful.
- [ ] Mark scenarios that cannot be executed automatically.
- [ ] Avoid duplicate/redundant scenarios.
- [ ] Support domain-specific scenario profiles later without contaminating the general core.

## Phase 4 — QA Memory

Goal: accumulate confirmed QA knowledge over time.

Planned capabilities:

- [ ] Store confirmed human QA findings.
- [ ] Store reusable regression rules.
- [ ] Link rules to components/routes/states/symbols.
- [ ] Recall relevant historical findings when related code changes.
- [ ] Promote confirmed bugs into permanent regression scenarios.
- [ ] Distinguish project-specific knowledge from generic QA principles.

## Phase 5 — Final Gate

Goal: produce a strict final QA decision from evidence.

Final outputs only:

- [ ] PASS
- [ ] BLOCK
- [ ] MANUAL REVIEW REQUIRED

Rules:

- [ ] Product bug evidence → BLOCK.
- [ ] Critical relevant scenario unverified → MANUAL REVIEW REQUIRED or BLOCK based on policy.
- [ ] Environment/test setup failure must not be misreported as a product bug.
- [ ] Test failure classification should distinguish product bug, test/config issue, environment failure, flake, and unreachable state.
- [ ] PASS requires sufficient evidence for all important planned scenarios.

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
- Each major QGate subsystem receives a dedicated maintained document when implementation begins.
- Documentation must explain technical architecture and user/business workflow.
- Relevant documentation must be updated in the same feature branch whenever code behavior/contracts change.
- `QGATE_PROGRESS.md` must be updated after every meaningful merged feature.

## Current Next Step

**Design and implement Project Intelligence V1 on a dedicated feature branch.**

The first implementation should establish the source adapter + bounded project index + structured output foundation before attempting broad AI semantic analysis.

Do not start Impact Analysis, Scenario Intelligence, QA Memory, or Final Gate implementation deeply until Project Intelligence produces a useful, tested, scalable project map.

## Definition of QGate V1 Success

QGate V1 is successful when, for a real code change, it can:

1. Understand the affected code area.
2. Identify realistic impacted states.
3. Generate relevant test scenarios.
4. Execute the automatable scenarios in a real browser.
5. Collect evidence.
6. Distinguish product bugs from test/environment failures.
7. Use relevant historical QA knowledge.
8. Return PASS, BLOCK, or MANUAL REVIEW REQUIRED with reasons/evidence.

## Progress Update Rule

After every meaningful merged feature:

1. Update this file.
2. Check completed items.
3. Add any newly discovered requirement.
4. Record major architectural decisions if they affect future work.
5. Update `Current Next Step` so development stays focused.
6. Update relevant documentation according to `docs/README.md`.

If a proposed task does not clearly support this roadmap, stop and question whether it belongs in QGate before implementing it.
