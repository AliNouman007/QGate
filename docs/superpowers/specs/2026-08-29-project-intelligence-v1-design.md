# Project Intelligence V1 Design

## Purpose

Project Intelligence converts a supplied source project into structured, evidence-backed knowledge that later QGate stages can use for impact analysis and scenario generation. The core is general-purpose and must not encode marketplace-specific assumptions.

## Scope

V1 provides a deterministic, bounded foundation that works without an LLM:

1. source adapter contract;
2. local folder and ZIP sources;
3. bounded file inventory with ignore rules, language/tooling detection, and file-role classification;
4. structural import/dependency graph for common Python and JavaScript/TypeScript imports;
5. behavioral fact extraction for conditions, auth/permission, feature flags, loading/error/empty states, browser storage, and responsive signals;
6. heuristics that distinguish likely behavioral conditions from technical guards without pretending certainty;
7. bounded semantic evidence-pack contract plus a deterministic fallback classifier;
8. structured ProjectKnowledge output with evidence, confidence, coverage gaps, analysis metadata, and source fingerprint;
9. JSON knowledge store outside the target project;
10. incremental re-analysis using per-file content hashes, reusing unchanged file analysis while rebuilding affected graph/summary data;
11. human-readable project map and CLI;
12. stronger React, Next.js, and TypeScript framework understanding for common frontend projects;
13. richer semantic classification over bounded evidence packs, while deterministic facts remain authoritative;
14. a local API read model for persisted ProjectKnowledge;
15. a dashboard Project Map that visualizes the latest persisted knowledge without creating a second analysis engine.

V1 does not require cloud or local LLM access. LLM enrichment is optional and must consume bounded evidence packs through the semantic-classifier interface; it may never receive an unrestricted whole-repository dump.

## Architecture

A workspace package, `qgate-project-intelligence`, owns Project Intelligence. Keeping it in a dedicated package isolates code-understanding responsibilities from Suitest execution, MCP, DB, and agent packages.

Data flow:

`ProjectSource -> ProjectScanner -> per-file analysis -> framework facts -> dependency graph -> bounded semantic classification -> ProjectKnowledge -> JsonKnowledgeStore / report`

Dashboard flow:

`JsonKnowledgeStore -> API read endpoint -> web Project Map`

Incremental flow:

`previous ProjectKnowledge + current source -> compare file hashes -> reuse unchanged FileAnalysis -> re-analyze changed/new files -> drop removed files -> rebuild graph/summary -> persist new knowledge`

## Source adapters

`ProjectSource` exposes a stable `root` and `iter_files()` contract. `LocalPathSource` analyzes an existing directory without modifying it. `ZipProjectSource` extracts an archive into a temporary directory owned by the adapter and cleans it up after analysis. Transport-specific adapters such as GitHub can be added later without changing the scanner.

## Bounded scanning

`AnalysisBudget` limits maximum discovered files, bytes read per file, total source bytes, and directory depth. Default ignored directories include VCS metadata, dependencies, build outputs, caches, virtual environments, and generated coverage artifacts. When a budget or unsupported binary/encoding construct prevents analysis, the knowledge output records a coverage gap rather than silently omitting it.

## Static facts and evidence

Every file gets a `FileAnalysis` containing basic metadata, import facts, behavioral condition facts, framework facts, and evidence references. Evidence contains the relative path, line number, excerpt, and fact kind. Structural graph edges reference evidence where available.

Regex/line parsing is intentionally conservative in V1. It supports common import forms and recognizable conditions but records coverage gaps for unsupported constructs. Future AST parsers can replace internal extractors without changing the public models.

## React / Next.js / TypeScript understanding

The V1 frontend specialization remains framework-specific but domain-agnostic. It recognizes common high-value patterns without assuming any business domain.

React understanding includes:

- component declarations and exported components;
- React hooks, including custom hooks;
- context/provider usage;
- common conditional JSX/state signals already represented by behavioral facts.

Next.js understanding includes:

- App Router special files (`page`, `layout`, `loading`, `error`, `not-found`, `template`, `route`);
- Pages Router files under `pages/`;
- dynamic route segments such as `[id]`, `[...slug]`, and `[[...slug]]`;
- `use client` / `use server` boundaries;
- common navigation/runtime APIs such as `useRouter`, `usePathname`, `useSearchParams`, `redirect`, `notFound`, `cookies`, and `headers`.

TypeScript understanding includes:

- exported interfaces, type aliases, enums, and typed React props when statically obvious;
- file/module role enrichment without attempting whole-program type inference.

These facts are evidence-backed metadata for later reasoning; they do not replace TypeScript's compiler or Next.js runtime behavior.

## Behavioral classification

A condition is not automatically a QA state. V1 tags conditions with categories such as `auth`, `permission`, `feature_flag`, `loading`, `error`, `empty`, `storage`, `responsive`, `general`, or `technical_guard`. Heuristics use variable names, operators, early-return patterns, and surrounding text. Confidence is explicit (`high`, `medium`, `low`) and uncertain facts remain facts rather than being promoted to guaranteed states.

## Semantic classification contract

`SemanticClassifier` accepts only a bounded `EvidencePack` built from deterministic facts and framework context. A semantic result can add a human-friendly state label, state kind, explanation, confidence, and whether runtime verification is required.

The deterministic fallback classifier groups obvious facts without an LLM. An optional AI-backed classifier may be wired through the existing QGate/Suitest agent provider layer later or at runtime, but it must obey these invariants:

- never invent source facts;
- preserve evidence references;
- never silently raise confidence above the supporting evidence;
- mark uncertain or runtime-dependent results as needing runtime verification;
- remain bounded by pack count and facts per pack.

Project Intelligence remains useful in ZERO/no-LLM mode; AI enriches meaning but is not the source of truth.

## Persistence

`JsonKnowledgeStore` writes knowledge under a caller-supplied QGate data directory, never inside the target project. Each project has a stable storage key derived from source identity. Stored metadata includes schema version, analyzer version, timestamp, source fingerprint, and per-file hashes.

The store also supports listing persisted project summaries and selecting the most recently analyzed project. The API uses only this read model; it does not scan arbitrary server paths on behalf of a web request.

## API read model

The API exposes authenticated read-only Project Intelligence endpoints backed by `JsonKnowledgeStore`:

- list persisted project maps;
- return the latest persisted project map;
- return a persisted project map by stable source id.

The knowledge directory is configured outside target projects. The API must not accept arbitrary local filesystem paths from the browser.

## Dashboard Project Map

The web dashboard reads the Project Intelligence API and renders a compact Project Map containing:

- project/source identity and analysis time;
- detected languages/frameworks;
- route/page/component counts;
- shared/reused modules;
- meaningful behavioral state categories;
- selected route/component/framework facts with evidence;
- coverage gaps and runtime-verification warnings.

The dashboard is a visualization of persisted knowledge, not a separate scanner or classifier.

## CLI

`qgate-project-intelligence analyze <path>` analyzes a directory or ZIP. Optional `--store-dir` persists JSON. `--json` prints structured JSON; otherwise a concise project map is printed. Optional `--previous <knowledge.json>` enables incremental reuse explicitly.

## Testing

Tests use temporary fixture projects and cover:

- ignore/budget behavior;
- language/file-role detection;
- Python and JS/TS import graph extraction;
- component/module reuse counts;
- behavioral condition versus technical guard classification;
- auth/storage/responsive facts;
- React components/hooks/context extraction;
- Next.js App Router and Pages Router route detection;
- Next.js client/server boundary and runtime API detection;
- TypeScript declarations relevant to project understanding;
- semantic evidence-pack enrichment and uncertainty handling;
- ZIP ingestion;
- persistence outside the target repo;
- store listing/latest selection;
- API read endpoints;
- dashboard Project Map loading, empty, and populated states;
- incremental reuse when only one file changes;
- human-readable report generation.

The package remains in the uv workspace, mypy path, and default pytest testpaths. API and web tests are updated only where their contracts change.

## Documentation

`docs/PROJECT_INTELLIGENCE.md` is the subsystem documentation. `docs/README.md` links to it. `QGATE_PROGRESS.md` is updated on the feature branch to reflect implemented V1 capabilities; the progress becomes canonical only when the PR is merged.

## Safety and non-goals

- Never modify the analyzed target project.
- Never require the target project to install QGate dependencies.
- No whole-repo LLM prompts.
- No framework-specific marketplace/business behavior.
- No automatic test generation or final QA decision in this phase.
- No Impact Analysis implementation in PR #1.
- No arbitrary server-path analysis initiated from the browser.
- No unrelated Suitest refactor.
