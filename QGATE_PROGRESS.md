# QGate — Goal, Scope & Progress Tracker

This file is the single source of truth for QGate development.

## Primary Goal

Build QGate as a local, developer-owned AI QA Gate for the current marketplace frontend project.

QGate should understand the codebase, discover meaningful states and scenarios, execute real browser tests, collect evidence, learn from human QA findings, and return one of three outcomes:

- PASS
- BLOCK
- MANUAL REVIEW REQUIRED

QGate is not meant to become another generic AI code reviewer.

## Core Product Direction

Use Suitest as the execution/platform foundation and add QGate-specific intelligence on top.

Core flow:

Code / PR / branch diff
→ Project Intelligence
→ Impact Analysis
→ Scenario Intelligence
→ Suitest / Playwright execution
→ Evidence collection
→ QA Memory
→ Final Gate

## Important Rules — Do Not Drift

- Focus first on the current marketplace project, not generic multi-project support.
- Do not rebuild capabilities Suitest already provides unless there is a strong reason.
- Prefer real browser/runtime evidence over LLM guesses.
- The LLM is the reasoning layer, not the source of truth.
- Source of truth = code + runtime browser + DOM/CSS/network/console evidence + QA memory.
- If an important scenario was not verified, QGate must not silently return PASS.
- QGate V1 detects and reports; it should not automatically fix production code.
- Keep QGate isolated from the company repository. Do not inject QGate dependencies/config into the company project unless explicitly approved.
- Keep changes small, testable, and traceable.
- Every Antigravity implementation task must report files changed, per-file change summary, reason, tests, branch, commit SHA, and any unrelated changes.

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

## QGate Intelligence Roadmap

### Phase 1 — Project Intelligence

Goal: build a reliable structural and behavioral map of the target frontend repository.

Planned capabilities:

- [ ] Scan routes/pages.
- [ ] Scan components.
- [ ] Build import/dependency graph.
- [ ] Detect where components are reused.
- [ ] Detect conditional rendering and meaningful state branches.
- [ ] Detect auth-related conditions.
- [ ] Detect feature flags.
- [ ] Detect responsive/breakpoint logic where useful.
- [ ] Detect important props/state/API dependencies.
- [ ] Persist project knowledge outside the company repository.
- [ ] Produce a human-readable Project Map.

Validation target for V1:

- [ ] Product Card / PLP area.

### Phase 2 — Impact Analysis

Goal: given a code change or PR diff, determine realistic blast radius and relevant states.

Planned capabilities:

- [ ] Read changed files/lines.
- [ ] Classify change type: UI, CSS, state, API, auth, pricing, routing, shared component, etc.
- [ ] Trace direct dependencies.
- [ ] Trace indirect/reused component impact.
- [ ] Identify affected routes/flows.
- [ ] Identify affected state combinations.
- [ ] Attach evidence/reason for each claimed impact.
- [ ] Produce structured Impact Report.

### Phase 3 — Scenario Intelligence

Goal: turn project knowledge + impact report into high-value QA scenarios.

Planned capabilities:

- [ ] Generate realistic state variants from code evidence.
- [ ] Prioritize likely/reachable states over purely theoretical states.
- [ ] Include known critical state pairs such as rating/no-rating, guest/authenticated, wallet/no-wallet, mobile/desktop.
- [ ] Generate E2E scenarios for Suitest/Playwright.
- [ ] Generate cross-state comparison scenarios where useful.
- [ ] Mark scenarios that cannot be executed automatically.
- [ ] Avoid duplicate/redundant scenarios.

### Phase 4 — QA Memory

Goal: accumulate marketplace-specific QA knowledge over time.

Planned capabilities:

- [ ] Store confirmed human QA findings.
- [ ] Store reusable regression rules.
- [ ] Link rules to components/routes/states.
- [ ] Recall relevant historical findings when related code changes.
- [ ] Promote confirmed bugs into permanent regression scenarios.
- [ ] Distinguish project-specific knowledge from generic QA principles.

Example memory:

`ProductCard + no rating → must not reserve empty rating-space height.`

### Phase 5 — Final Gate

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

## First Marketplace Areas

Do not attempt the entire marketplace at once.

Priority order:

1. [ ] Product Card / PLP / Search results
2. [ ] Checkout / Cart / Payment-related UI
3. [ ] PDP / Product details

The order may change only if a real work need gives another area higher priority.

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

- Unit tests for isolated QGate logic.
- Integration tests for module/database/API interaction.
- E2E tests with Playwright for real user flows.
- Runtime DOM/computed CSS evidence for UI issues.
- Screenshot/visual evidence where useful.
- Console/network evidence where relevant.

## Current Next Step

**Build Project Intelligence V1 and validate it on Product Card / PLP.**

Do not start Impact Analysis, Scenario Intelligence, QA Memory, or Final Gate implementation deeply until Project Intelligence produces a useful and validated project map.

## Definition of QGate V1 Success

QGate V1 is successful when, for a real marketplace change, it can:

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

If a proposed task does not clearly support this roadmap, stop and question whether it belongs in QGate before implementing it.
