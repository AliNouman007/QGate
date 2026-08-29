# QGate Documentation

This folder is the maintained documentation set for QGate.

The goal is that a new developer or AI agent can understand what QGate does, why it exists, how data moves through the system, where each subsystem lives, and what must be updated when code changes.

## Start here

Read in this order:

1. `../AGENTS.md` — mandatory engineering and AI-agent rules.
2. `../QGATE_PROGRESS.md` — product goal, roadmap, completed work, and current next step.
3. `README.md` — this documentation map.
4. Then read only the documents relevant to the task.

## QGate product flow

At a high level:

Project source
→ Project Intelligence
→ Impact Analysis
→ Scenario Intelligence
→ Suitest/Playwright execution
→ Evidence collection
→ QA Memory
→ Final Gate

The target project may come from a GitHub repository, an extracted ZIP, or a local folder through a source adapter. QGate must keep its own knowledge and testing artifacts outside the target repository.

## QGate-specific documentation

As QGate evolves, major subsystems must have their own maintained docs:

- `PROJECT_INTELLIGENCE.md` — source ingestion, indexing, structural graph, behavioral state extraction, evidence, confidence, incremental analysis.
- `IMPACT_ANALYSIS.md` — diff/change analysis and blast-radius reasoning.
- `SCENARIO_INTELLIGENCE.md` — scenario generation, prioritization, reachability, and manual-review handling.
- `QA_MEMORY.md` — confirmed findings, reusable regression knowledge, linking, and recall.
- `FINAL_GATE.md` — PASS/BLOCK/MANUAL REVIEW REQUIRED decision policy.

Create these files when their implementation begins; do not create speculative documentation that describes code which does not exist yet.

## Existing Suitest foundation docs

These remain useful because QGate is currently built on the Suitest codebase:

- `ARCHITECTURE.md` — current platform/service topology and package boundaries.
- `API.md` — API contracts.
- `DATA_MODEL.md` — database model and schema behavior.
- `AI_AGENT.md` — current agent/LLM foundation.
- `MCP_PLUGINS.md` — MCP integration and routing.
- `BLACKBOX_UI_TESTING.md` — browser/black-box testing foundation.
- `CAPABILITY_TIERS.md` — capability gating.
- `AUTONOMY.md` — autonomy/side-effect policy.
- `DEPLOYMENT.md` — deployment/local-runtime information.
- `ROADMAP.md`, `PRODUCT.md`, and other Suitest docs — upstream historical/product context; QGate-specific direction is controlled by `../QGATE_PROGRESS.md`.
- `SUITEST_AUDIT.md` — initial analysis of the Suitest foundation for QGate.

If an upstream Suitest document conflicts with an approved QGate decision, QGate's `AGENTS.md` and `QGATE_PROGRESS.md` take precedence. Update the relevant documentation when the implementation changes.

## Documentation update matrix

When code changes, update documentation in the same branch/commit where practical:

| Change type | Documentation to review/update |
| --- | --- |
| Product scope / roadmap | `../QGATE_PROGRESS.md` |
| New major QGate subsystem | subsystem doc + this index |
| Package/service/data-flow architecture | `ARCHITECTURE.md` and/or subsystem doc |
| API endpoint/request/response | `API.md` |
| Database/schema/model | `DATA_MODEL.md` |
| MCP provider/routing/tool contract | `MCP_PLUGINS.md` |
| Agent/LLM behavior | `AI_AGENT.md` or subsystem doc |
| Local setup/config/env behavior | relevant setup/deployment doc + `.env.example` |
| User-facing workflow | relevant subsystem/product workflow doc |
| New known limitation | relevant feature doc + roadmap if it affects scope |

## Documentation quality rules

Documentation must:

- describe what exists, not an imagined future implementation;
- explain both **why** and **how**;
- use plain English and define important terms;
- show the business/product workflow as well as the technical flow;
- name the owning folders/packages where useful;
- call out limitations, assumptions, and failure modes;
- stay synchronized with code and tests;
- avoid duplicating the same source of truth across many documents.

When a major architectural decision is made, record it in the most relevant subsystem/architecture doc so future contributors do not have to reconstruct the reasoning from chat history.

## Definition of documentation-complete

A meaningful feature is documentation-complete when a new developer can answer:

1. What problem does this feature solve?
2. Where does it live in the codebase?
3. What inputs does it accept?
4. What outputs/state does it produce?
5. How does it interact with other QGate modules?
6. How is it tested?
7. What are its important limitations or unknowns?
8. What user/business workflow does it enable?
