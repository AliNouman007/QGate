# AGENTS.md — Mandatory QGate Engineering Rules

> This is the first file every AI coding agent must read before changing QGate. It applies to ChatGPT, Codex, Antigravity, Claude Code, Cursor, Cline, and any future coding agent.

## 1. Mission

QGate is a developer-owned AI QA gate built on the Suitest foundation. Its job is to understand a supplied codebase, identify meaningful project states and risks, generate high-value QA scenarios, execute evidence-backed tests, learn from confirmed QA findings, and return a strict result: PASS, BLOCK, or MANUAL REVIEW REQUIRED.

QGate must remain general-purpose. Do not hard-code marketplace-specific assumptions into the core. Domain-specific knowledge may be added later as optional profiles/adapters.

## 2. Mandatory reading order before coding

1. `AGENTS.md` — engineering rules and guardrails.
2. `QGATE_PROGRESS.md` — current product goal, completed work, roadmap, and next task.
3. `docs/README.md` — documentation map and update requirements.
4. Read only the relevant existing Suitest/QGate docs required by the task, such as `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATA_MODEL.md`, `docs/MCP_PLUGINS.md`, `docs/AI_AGENT.md`, or `CLAUDE.md`.

If a task conflicts with `QGATE_PROGRESS.md`, stop and resolve the conflict before implementation.

## 3. Do not drift

- Work only on changes that directly support the current QGate roadmap or an explicitly approved maintenance task.
- Do not add unrelated refactors, cleanup, dependency upgrades, abstractions, or feature work while implementing another task.
- Reuse existing Suitest capability instead of rebuilding it unless there is a documented reason.
- Keep QGate isolated from the user's target project. Do not inject QGate dependencies or config into the target repository unless explicitly approved.
- Do not silently broaden scope. If implementation uncovers a larger problem, report it separately.

## 4. Engineering approach

Before editing code:

1. Understand the requirement and success criteria.
2. Inspect existing implementation and folder structure.
3. Identify the smallest correct change.
4. Reuse existing functions/services/contracts when appropriate.
5. Decide which tests and documentation must change.
6. Only then implement.

Prefer the minimal solution that fully solves the problem. Do not create function-on-function abstractions, wrappers, services, helpers, or new layers without a concrete need.

Avoid premature generalization. Generalize only when there are multiple real callers/use cases or when the architecture explicitly requires an extension point.

## 5. Code quality rules

- Follow the existing monorepo and package boundaries.
- Put code in the folder that already owns that responsibility.
- Keep functions small enough to understand, but do not split simple logic into unnecessary helpers.
- Prefer explicit types and structured models over loose dictionaries or untyped values.
- Do not duplicate business logic.
- Do not hide important behavior in magic constants or implicit side effects.
- Do not hard-code credentials, secrets, production URLs, user-specific paths, or target-project assumptions.
- Preserve backward compatibility unless a breaking change is explicitly approved.
- Use existing error-handling, logging, repository, API, MCP, agent, and UI patterns before inventing new ones.
- Do not modify unrelated files simply to make formatting or style changes.

Existing upstream Suitest coding rules in `CLAUDE.md` remain applicable unless this file or an approved QGate architecture decision overrides them.

## 6. Project Intelligence design rule

Project Intelligence must be a scalable, general code-understanding engine.

Required principles:

- Accept project sources through adapters such as GitHub repositories, extracted ZIPs, or local folders.
- Convert source code into structured project knowledge rather than one giant prose summary.
- Use a hybrid approach: deterministic/static analysis for facts; AI only for semantic classification, grouping, prioritization, or explanation.
- Every AI-derived claim must be traceable to code evidence where possible.
- Record confidence and unresolved/unknown states instead of guessing.
- Do not treat every `if` statement as a meaningful QA state; distinguish technical guards from behaviorally relevant conditions.
- Scale with hierarchical scanning: lightweight whole-project index first, targeted deep analysis second.
- Support incremental re-analysis so large projects do not require a full deep scan after every change.
- Persist project knowledge outside the target repository.

## 7. Tests are mandatory

Every behavioral code change must include or update appropriate tests.

Use the smallest useful test level:

- Unit tests for isolated parsing, classification, transforms, and business logic.
- Integration tests when modules, database, API, runner, or services interact.
- E2E/Playwright tests for user-visible flows and browser behavior.
- Regression tests for every confirmed bug that could reasonably recur.

Rules:

- A feature is not complete because the code compiles.
- Do not delete or weaken an existing test merely to make a change pass unless the product requirement changed and the test is updated with a documented reason.
- Test failure due to environment/configuration must not be misrepresented as a product bug.
- Prefer deterministic fixtures and reproducible tests.

## 8. Documentation is part of the change

Documentation must evolve with the code. A code change is incomplete when it changes architecture, behavior, workflow, public API, data model, setup, configuration, or user-visible behavior without updating the relevant docs.

At minimum:

- Update `QGATE_PROGRESS.md` after every meaningful merged feature.
- Update `docs/README.md` when docs are added/removed/reorganized.
- Update architecture docs when module boundaries, dependencies, or data flow change.
- Update API/data-model/configuration docs when those contracts change.
- Add feature-specific docs for major QGate subsystems such as Project Intelligence, Impact Analysis, Scenario Intelligence, QA Memory, and Final Gate.

Documentation should explain both technical behavior and the product/business workflow in plain English so a new developer can understand why the feature exists and how data moves through the system.

## 9. Change isolation and Git discipline

- Use a focused feature/fix branch for meaningful implementation work.
- Keep each branch centered on one purpose.
- Do not mix unrelated fixes into a feature branch.
- Do not merge until relevant tests pass and the diff has been reviewed.
- Preserve working baselines; avoid destructive rewrites unless explicitly approved.

## 10. Mandatory completion report for AI agents

Every implementation task must report:

- TASK: PASS/FAIL
- BRANCH
- COMMIT SHA
- FILES CHANGED
- CHANGE SUMMARY PER FILE
- WHY EACH CHANGE WAS NEEDED
- TESTS RUN
- TEST RESULTS
- DOCUMENTATION UPDATED
- UNEXPECTED/UNRELATED CHANGES: YES/NO
- BLOCKERS

Do not claim success without running the relevant verification available in the working environment.

## 11. QGate safety philosophy

- Deterministic evidence is preferred over LLM guesses.
- AI is a reasoning layer, not the source of truth.
- Runtime/browser/DOM/network/code evidence should support QA conclusions.
- If an important scenario is unknown or unverified, do not silently return PASS.
- V1 should detect and report; it should not automatically modify the user's production project.

## 12. Stop conditions

Stop and ask for a decision before coding when:

- the requested work conflicts with the current roadmap;
- the change requires a significant new dependency or architectural layer;
- the only solution requires modifying the user's target project;
- requirements are materially ambiguous and the ambiguity changes architecture;
- the implementation would introduce a breaking change outside the approved scope.
