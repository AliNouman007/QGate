# Project Intelligence

Project Intelligence is QGate's code-understanding layer. It converts a supplied source project into structured, evidence-backed knowledge that later QGate stages can use for Impact Analysis and Scenario Intelligence.

## Business workflow

A developer gives QGate a project source. Project Intelligence analyzes it without modifying the target repository, builds a bounded structural and behavioral map, records uncertainty/unsupported areas, and persists the result in QGate-owned storage. The dashboard reads that persisted knowledge as a Project Map. Later QGate stages reuse the same knowledge instead of repeatedly asking an LLM to rediscover the project from scratch.

Current V1 flow:

`local folder / ZIP -> bounded inventory -> static facts -> React/Next/TypeScript facts -> dependency graph -> bounded semantic states -> ProjectKnowledge -> JSON store -> API -> Project Map`

Optional AI enrichment flow:

`bounded EvidencePack -> existing LLMProvider -> validated semantic response -> evidence/confidence guardrails -> SemanticState`

GitHub remains a source-adapter extension point. A GitHub connector can materialize/checkout a repository and feed the same `ProjectSource` contract rather than coupling GitHub transport logic into the analyzer.

## Code ownership

Project Intelligence core lives in `packages/project-intelligence/`.

Main modules:

- `models.py` — structured contracts for evidence, confidence, framework facts, routes, symbols, semantic states, budgets, and ProjectKnowledge.
- `source.py` — read-only source adapter protocol plus local folder and ZIP implementations.
- `scanner.py` — bounded inventory, ignore rules, language and file-role detection.
- `extractors.py` — conservative import and behavioral condition extraction.
- `frameworks.py` — React, Next.js, and TypeScript frontend-specific static understanding.
- `graph.py` — internal dependency resolution and reuse counts.
- `semantic.py` — bounded evidence-pack boundary, richer semantic state model, and deterministic fallback classifier.
- `analyzer.py` — orchestration, framework integration, semantic state generation, fingerprinting, and incremental reuse.
- `store.py` — JSON persistence, stable project keys, project listing, and latest-analysis selection.
- `report.py` — human-readable Project Map for CLI output.
- `cli.py` — local analysis entrypoint.

Optional AI semantic enrichment lives in the existing agent layer:

- `packages/agent/src/suitest_agent/project_intelligence_semantic.py` — provider-backed bounded semantic enrichment using the existing `LLMProvider` contract.

Dashboard/API integration lives in:

- `apps/api/src/suitest_api/routers/project_intelligence.py`
- `apps/web/src/hooks/use-project-intelligence.ts`
- `apps/web/src/routes/_app/project-map.tsx`

## Inputs

### Local directory

`LocalPathSource` accepts an existing directory. QGate reads the project but does not install dependencies, create config, or write artifacts into the target project.

### ZIP archive

`ZipProjectSource` extracts into a temporary QGate-owned directory, rejects path traversal outside that directory, analyzes the project, then deletes the temporary extraction.

### Future adapters

GitHub, GitLab, cloud-drive, or workspace adapters should implement/materialize the same source contract. Authentication and transport belong in the adapter, not in the scanner.

## Scaling and bounded analysis

`AnalysisBudget` keeps analysis predictable on both small and large repositories:

- maximum files;
- maximum bytes per file;
- maximum total source bytes;
- maximum directory depth.

Common dependency/build/cache directories such as `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, and coverage outputs are ignored by default.

When QGate cannot analyze something because of a budget, binary content, encoding problem, or read failure, it records a `CoverageGap` rather than pretending the area was understood.

## Fast project index

Each included file becomes a `FileRecord` containing its relative path, size, SHA-256 content hash, detected language, and likely role (route, component, service, state, test, config, source, or other).

Per-file hashes power source fingerprints and incremental reuse.

## Structural graph

V1 recognizes common Python and JavaScript/TypeScript import forms and resolves supported internal paths against the indexed project. Resolved relationships become `DependencyEdge` records with source evidence.

Reuse counts identify modules/components imported by multiple callers. This becomes especially important to future Impact Analysis because a change in a shared component can have a larger blast radius than a change in one isolated page.

## Frontend framework intelligence

The core stays general-purpose, but V1 now has a frontend specialization for the frameworks currently most important to QGate: React, Next.js, and TypeScript. This specialization is domain-agnostic; it does not encode marketplace assumptions.

Framework inference uses project/package evidence rather than folder names alone. In particular, a generic project merely containing a `pages/` directory is not promoted to Next.js unless package/direct-import evidence supports it.

### React

QGate recognizes common evidence-backed patterns such as:

- function/const React components;
- exported components;
- built-in and custom-style `useX` hooks;
- `createContext` declarations;
- provider usage where statically visible.

### Next.js

QGate understands common Next.js routing and runtime signals:

- App Router special files: `page`, `layout`, `loading`, `error`, `not-found`, `template`, and `route`;
- Pages Router files under `pages/`;
- route groups in parentheses;
- dynamic segments such as `[id]`, `[...slug]`, and `[[...slug]]`;
- `use client` and `use server` boundaries;
- common APIs including `useRouter`, `usePathname`, `useSearchParams`, `redirect`, `notFound`, `cookies`, and `headers`.

Detected framework routes are stored as `RouteFact` records with router type, route kind, dynamic flag, and code evidence.

### TypeScript

V1 records statically obvious exported/local interfaces, type aliases, and enums as `SymbolFact` records. This is project understanding, not a replacement for TypeScript's compiler or full type graph.

## Behavioral facts

Project Intelligence does not treat every `if` as a QA state.

It extracts conditions/runtime signals and categorizes them as:

- auth;
- permission;
- feature flag/experiment;
- loading;
- error;
- empty;
- storage/cookie/session;
- responsive;
- general;
- technical guard.

Likely early-return/infrastructure guards are marked `technical_guard` and `meaningful=false`. User-visible/stateful conditions remain meaningful facts. Every fact carries expression, category, confidence, and exact code evidence.

Static facts do not prove runtime reachability. Scenario Intelligence and browser execution will handle that later.

## Semantic classification and AI boundary

Project Intelligence produces richer `SemanticState` objects from bounded evidence packs. A semantic state contains:

- human-friendly label;
- state kind (`user_state`, `access_state`, `feature_state`, `data_state`, `viewport_state`, `runtime_state`, etc.);
- explanation;
- confidence;
- supporting evidence;
- `needs_runtime_verification` when static evidence is not enough.

`EvidencePack` includes deterministic behavioral facts plus bounded framework context from the same file. The core `SemanticClassifier` protocol keeps semantic reasoning behind a controlled contract.

### ZERO/no-LLM mode

`HeuristicSemanticClassifier` is the default. It is deterministic, conservative, and keeps Project Intelligence useful without an AI provider.

### Provider-backed AI enrichment

`packages/agent/src/suitest_agent/project_intelligence_semantic.py` provides optional AI enrichment through the existing provider-independent `LLMProvider` contract. It sends one already-bounded EvidencePack per call and validates a small structured JSON result.

Guardrails are enforced in code:

- the provider receives a bounded pack, never the whole repository;
- model output cannot provide or replace source evidence — QGate reattaches deterministic evidence itself;
- model-reported confidence is clamped so it cannot exceed supporting deterministic confidence;
- runtime-verification requirements from the deterministic fallback cannot be silently removed;
- invalid provider output or a provider error falls back to the deterministic heuristic state;
- AI never becomes the source of truth for project facts.

The synchronous analyzer does not automatically invoke an LLM. Provider-backed enrichment is an optional agent-layer step so ZERO mode stays reliable and the deterministic scanner remains independent of provider/network concerns.

## Structured ProjectKnowledge

`ProjectKnowledge` contains:

- analysis/schema versions and timestamp;
- stable source identity and fingerprint;
- project summary, including declared frontend framework context;
- per-file imports, behaviors, framework facts, routes, and symbols;
- dependency graph;
- semantic states;
- coverage gaps.

This structured model, not the prose report, is the contract future Impact Analysis consumes.

## Incremental analysis

When previous knowledge from the same analyzer version exists, unchanged files are reused by path/content hash. Changed/new files are re-read; removed files disappear; project-level graph, summaries, semantic states, and fingerprint are rebuilt from current knowledge.

Framework declarations from package manifests are part of the analysis context. If that context changes (for example Next.js is added/removed), unchanged frontend files are re-analyzed instead of reusing stale framework interpretation.

The CLI automatically looks up previous knowledge for the same source identity in its configured store unless `--previous` explicitly supplies another knowledge file.

## Persistence

By default the CLI stores ProjectKnowledge under:

`~/.qgate/project-intelligence`

The location can be overridden with `--store-dir`. The API uses `SUITEST_PROJECT_INTELLIGENCE_DIR` and defaults to the same location. This storage is outside target repositories.

Each source has a stable 24-character hashed key. `JsonKnowledgeStore` can load by source identity/key, list persisted projects, and return the latest analysis.

## Local Project Intelligence API

Project Map endpoints are read-only and available only when `SUITEST_MODE=local`. Normal workspace authentication still applies.

- `GET /api/v1/project-intelligence/projects` — persisted project summaries.
- `GET /api/v1/project-intelligence/latest` — latest full ProjectKnowledge.
- `GET /api/v1/project-intelligence/projects/{key}` — one persisted ProjectKnowledge by stable key.

The browser never supplies an arbitrary filesystem path. Analysis happens locally through the source/CLI path; the dashboard only reads already-persisted knowledge.

## Dashboard Project Map

The dashboard route `/project-map` visualizes the latest persisted knowledge. It shows:

- files, routes, components, and runtime-verification count;
- detected languages and frameworks;
- behavioral categories;
- evidence-backed Next routes and React components;
- semantic states/confidence/runtime warnings;
- reused internal modules;
- coverage gaps;
- source identity, fingerprint, and analysis time.

A 404 from the local API means “No project analyzed yet,” not an application failure.

## CLI usage

Analyze a local project (and persist it to the default QGate store):

```bash
qgate-project-intelligence analyze /path/to/project
```

Analyze a ZIP:

```bash
qgate-project-intelligence analyze /path/to/project.zip
```

Use another QGate-owned store and print JSON:

```bash
qgate-project-intelligence analyze /path/to/project --store-dir /path/to/qgate-data --json
```

Explicitly reuse a knowledge file:

```bash
qgate-project-intelligence analyze /path/to/project --previous /path/to/knowledge.json
```

Budgets are configurable with `--max-files`, `--max-file-bytes`, `--max-total-bytes`, and `--max-depth`.

## Testing

Core tests cover bounded scanning, structural/behavioral maps, incremental reuse, ZIP ingestion, persistence, and reporting.

Frontend-intelligence tests cover React components/hooks/context, Next App/Pages routes and dynamic segments, Next runtime APIs/client boundaries, TypeScript declarations, false-positive framework avoidance, framework-manifest invalidation, semantic evidence/context, and store list/latest/key behavior.

Agent tests cover provider-backed semantic enrichment, evidence preservation, confidence clamping, and invalid-model-output fallback.

API tests cover authenticated local Project Map list/latest behavior, empty-store handling, and hiding the read model in server mode.

Web tests cover Project Map empty and populated states. Local verification must also regenerate/check TanStack's generated route tree and run the web build.

## Current limitations

V1 deliberately remains conservative:

- no GitHub network/auth adapter yet; repositories can be materialized externally and analyzed through the source contract;
- React/Next/TypeScript extraction is static/regex-based, not a full AST/compiler/Next manifest parser;
- TypeScript path aliases such as `@/` are not yet resolved by the dependency graph;
- complex dynamic imports, generated routes, metaprogramming, and compiler-only relationships can be missed;
- provider-backed AI semantic enrichment exists but is optional and is not automatically invoked by the synchronous analyzer;
- static conditions do not prove runtime reachability.

These limitations must be surfaced rather than compensated for with guesses.

## Relationship to later QGate stages

Project Intelligence answers: **What does this project contain, how is it connected, and what meaningful code states/signals are visible?**

Impact Analysis will answer: **What could this specific change affect?**

Scenario Intelligence will answer: **Which realistic states should we test?**

Suitest/Playwright will answer: **What actually happens at runtime?**

QA Memory and Final Gate will turn that evidence into durable regressions and PASS/BLOCK/MANUAL REVIEW REQUIRED decisions.
