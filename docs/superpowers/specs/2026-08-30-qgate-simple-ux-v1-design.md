# QGate Simple UX V1 — Design

## Goal
Make QGate understandable and usable from the UI with one obvious flow:

`Add/Select Project → Analyze Project → Review Scenarios/Test Cases → Run → See Result`

The UI must show data only for the currently selected project. When the current acceptance criteria are met, stop; do not add speculative hardening or unrelated polish.

## Product Principle
QGate should prefer a sufficient, verified, maintainable user flow over theoretical completeness. No over-engineering, over-validation, unnecessary refactors, or speculative features in this milestone.

## Default User Journey
1. **Project** — user adds or selects a local project.
2. **Analyze** — QGate analyzes that selected project and builds its project intelligence/project map.
3. **Scenarios / Test Cases** — QGate shows project-specific scenarios and test cases. AI generation belongs here.
4. **Run** — user runs selected tests/scenarios.
5. **Result** — user sees PASS / BLOCK / MANUAL REVIEW plus concise evidence. Technical browser details are secondary drill-down.

## Default Navigation
Keep the primary sidebar small:

- Dashboard / Project Overview
- Test Cases
- Test Runs
- Defects

Advanced technical views should not dominate the default navigation:

- Project Map: move into Project Overview as a tab/section or otherwise make secondary.
- Impact Analysis: show only when a change/diff/PR workflow exists for the selected project.
- Scenarios: keep accessible as part of testing workflow, but do not present it as an unexplained standalone technical concept if it can be reached from Test Cases / Analyze flow.
- Browser Execution: remove from primary sidebar; expose as execution details from a run.

Do not delete the underlying routes or capabilities in this milestone unless strictly necessary. Prefer hiding/moving navigation over architectural removal.

## Workspace / Demo Noise
In local-auth QGate usage, seeded demo workspaces such as `E2E Gate`, `E2E Zero`, `E2E Run`, `E2E Fail`, `QA Test` must not distract or masquerade as active user projects. Use the smallest safe UI treatment:

- hide irrelevant demo workspace switching in local mode, or
- clearly label demo-only entries and prevent broken switching behavior from being presented as a real user workflow.

Do not redesign the workspace model or delete seed data in this milestone.

## Project Scoping — Critical Correctness Rule
Every Project Map, Impact Analysis, Scenario, Test Case, Run, and Defect shown in project context must be scoped to the selected project/source.

When the selected project changes:

- stale data from another project must not remain visible;
- `/admin`, `/category`, `/search`, or any other routes from unrelated fixtures must never appear under `qgate-test-shop` unless they truly exist in that selected project's analyzed data;
- if no analysis exists for the selected project, show a clear empty state / Analyze action rather than fallback demo data.

Cross-project stale data is a correctness bug, not cosmetic noise.

## Project Overview / Analyze
For a newly selected project:

- show project identity/path clearly;
- provide one obvious `Analyze Project` action if project intelligence is not available;
- after analysis, show a concise status and useful summary (files/components/routes/states) without forcing the user to understand internal pipeline terms;
- Project Map may be a secondary tab/detail under this overview.

Do not invent a new analysis engine. Reuse existing Project Intelligence APIs/data.

## Scenarios and AI Generation
Scenario generation remains code/project-intelligence-first. Browser exploration is secondary evidence/discovery, not the primary source of truth.

The Test Cases / Scenarios workflow should make these actions obvious:

- Generate with AI
- Create manually
- Review generated scenario/test
- Edit/skip if needed
- Run

Use existing LLM integration and Generate UI where possible. This milestone should wire/clarify existing capability rather than build a new AI subsystem.

## Browser Execution
Browser Execution is an internal execution/evidence layer. The normal user should see:

- Running
- Passed / Failed / Unverified
- concise evidence
- `View execution details` when needed

The existing Browser Execution page may remain routable but should not be a primary sidebar destination.

## Defects
Defects belong to the selected project and can remain a primary destination because they represent verified issues. Do not redesign defect management in this milestone.

## AI Panel
Do not redesign the AI side rail in this milestone. If it is hidden or unavailable in some routes, that is not a blocker unless AI test generation itself depends on it. Primary AI generation should be discoverable from Test Cases / Scenarios through the existing Generate flow.

## Acceptance Criteria
The milestone is complete when all of the following are true:

1. A user can add/select `qgate-test-shop` from the UI.
2. The selected project identity is obvious.
3. Project-specific analysis can be triggered or clearly shown from the UI.
4. Project Map / routes shown for the shop come only from the shop; no stale demo routes leak in.
5. User can reach project-specific Test Cases / Scenarios without understanding internal architecture.
6. User can manually create a test case.
7. Existing AI `Generate` flow is clearly available and uses the selected project context; if the underlying LLM is unavailable, the UI reports that cleanly rather than showing unrelated data.
8. User can run a test and see the result.
9. Browser Execution is secondary/drill-down, not a primary confusing workflow.
10. Demo workspace noise is hidden or clearly demoted in local mode.

Once these acceptance criteria pass, STOP. No sidebar redesign beyond what is required, no workspace rewrite, no AI subsystem rewrite, no new dashboards, no speculative browser-crawling scenario generator.

## Non-Goals
- Rebuild Suitest from scratch.
- Remove existing advanced routes/capabilities.
- Rewrite workspace/database architecture.
- Build autonomous browser-only scenario generation.
- Redesign the AI rail.
- Add new analytics/coverage dashboards.
- General visual restyling.
- Cleanup every legacy/demo record.
- Additional hardening after acceptance criteria are satisfied.
