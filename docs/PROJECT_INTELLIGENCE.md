# Project Intelligence

Project Intelligence is QGate's code-understanding layer. It converts a supplied source project into structured, evidence-backed knowledge that later QGate stages can use for impact analysis and scenario generation.

## Business workflow

A developer gives QGate a project source. Project Intelligence analyzes the project without modifying it, builds a bounded structural and behavioral map, records uncertainty and unsupported areas, and stores the result outside the target repository. Later QGate stages use that knowledge instead of repeatedly asking an LLM to rediscover the project from scratch.

Current V1 flow:

`local folder / ZIP -> bounded inventory -> file analysis -> dependency graph -> behavioral facts -> ProjectKnowledge -> JSON store / project map`

GitHub is intentionally an adapter extension point rather than being coupled into the analyzer. A GitHub connector can materialize/checkout a repository and then provide the same `ProjectSource` contract.

## Code ownership

Project Intelligence lives in:

`packages/project-intelligence/`

Main modules:

- `models.py` — structured data contracts, evidence, confidence, budgets, knowledge output.
- `source.py` — read-only source adapter protocol plus local folder and ZIP implementations.
- `scanner.py` — bounded inventory, ignore rules, language and file-role detection.
- `extractors.py` — conservative import and behavioral fact extraction.
- `graph.py` — internal dependency resolution and reuse counts.
- `semantic.py` — bounded evidence-pack contract and deterministic fallback classifier.
- `analyzer.py` — orchestration, fingerprinting, and incremental reuse.
- `store.py` — JSON persistence under caller-controlled QGate storage.
- `report.py` — concise human-readable project map.
- `cli.py` — local analysis entrypoint.

## Inputs

### Local directory

`LocalPathSource` accepts an existing directory. The analyzer only reads files; it does not create configuration, dependencies, or artifacts inside the target project.

### ZIP archive

`ZipProjectSource` extracts into a temporary QGate-owned directory, rejects path traversal outside that directory, analyzes the extracted project, and cleans the temporary directory afterward.

### Future adapters

Any future GitHub, GitLab, cloud-drive, or workspace adapter should implement the same `ProjectSource` contract. Transport/authentication logic belongs in the adapter, not in the scanner or analyzer.

## Scaling and bounded analysis

Project Intelligence must remain predictable on large repositories. `AnalysisBudget` controls:

- maximum files;
- maximum bytes per file;
- maximum total bytes;
- maximum directory depth.

Common dependency/build/cache directories such as `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, and coverage outputs are ignored by default.

When a file or repository region cannot be analyzed because of a budget, binary content, encoding problem, or read failure, V1 records a `CoverageGap`. It does not silently pretend the area was understood.

## Fast project index

Each included file becomes a `FileRecord` with:

- relative path;
- byte size;
- SHA-256 content hash;
- detected language where known;
- likely role such as route, component, service, state, test, config, source, or other.

The content hash is the basis for source fingerprinting and incremental reuse.

## Structural graph

V1 recognizes common Python and JavaScript/TypeScript import forms and resolves internal relative/module paths against the indexed project. Resolved relations become `DependencyEdge` records with code evidence.

Reuse counts identify files imported by multiple internal callers. This is useful later for blast-radius analysis because highly reused components/modules deserve more attention.

V1 intentionally uses conservative static parsing without a third-party AST dependency. Unsupported alias systems, framework-specific generated routes, dynamic module resolution, and complex metaprogramming may appear as coverage gaps or unresolved imports rather than guessed relationships.

## Behavioral facts

Project Intelligence does not treat every `if` statement as a meaningful QA state.

V1 extracts condition/runtime signals and categorizes them as:

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

Likely early-return null/infrastructure guards are marked `technical_guard` and `meaningful=false`. Recognizable user-visible/stateful signals are kept as meaningful behavioral facts.

Every fact includes:

- original expression;
- category;
- confidence;
- meaningful flag;
- file, line, excerpt, and evidence kind.

These are facts/signals, not proof that a runtime state is reachable. Reachability belongs to later Scenario Intelligence/runtime verification.

## Semantic classification and AI boundary

V1 works without an LLM.

`EvidencePack` is the mandatory boundary for future AI semantic enrichment. Packs have hard fact/pack limits and contain deterministic facts plus their evidence. `SemanticClassifier` is the extension contract. `HeuristicSemanticClassifier` is the current deterministic fallback.

A future LLM implementation may improve naming/grouping/prioritization, but it must:

- consume bounded evidence packs, never unrestricted whole-repo dumps;
- preserve supporting evidence;
- record confidence;
- mark uncertain results as needing runtime verification rather than inventing certainty.

## Structured output

`ProjectKnowledge` contains:

- analysis metadata and versions;
- stable source identity and fingerprint;
- project summary;
- per-file analyses;
- dependency graph;
- behavioral facts;
- coverage gaps.

This structured representation is the source for future Impact Analysis, not the human-readable report.

## Incremental analysis

When a previous `ProjectKnowledge` object from the same analyzer version is provided, unchanged files are reused when their path and content hash match. New/changed files are re-read and re-analyzed; removed files disappear from the new knowledge object. Project-level summaries, dependency graph, and fingerprint are rebuilt from the current set.

This keeps deep work proportional to actual changes rather than repository size.

## Persistence

`JsonKnowledgeStore` writes JSON under a caller-supplied storage directory. Storage identity is derived from the source ID. The target project is never used as the persistence location unless a caller explicitly and incorrectly points the QGate store there; production integration should supply a dedicated QGate data directory.

## CLI usage

After workspace dependencies are synchronized:

```bash
qgate-project-intelligence analyze /path/to/project
```

Analyze a ZIP:

```bash
qgate-project-intelligence analyze /path/to/project.zip
```

Persist knowledge and print JSON:

```bash
qgate-project-intelligence analyze /path/to/project --store-dir /path/to/qgate-data --json
```

Reuse an earlier knowledge file:

```bash
qgate-project-intelligence analyze /path/to/project --previous /path/to/knowledge.json
```

Budgets can be overridden with `--max-files`, `--max-file-bytes`, `--max-total-bytes`, and `--max-depth`.

## Testing

`packages/project-intelligence/tests/test_project_intelligence.py` covers:

- ignore rules and file-role/language detection;
- internal TypeScript dependency graph;
- shared component reuse;
- meaningful state versus technical guard;
- auth/loading/responsive/storage signals;
- bounded scan coverage gaps;
- incremental changed-file reuse;
- ZIP ingestion;
- bounded semantic packs;
- JSON persistence outside the target fixture;
- human-readable report generation.

## Current limitations

V1 is deliberately a foundation, not a full compiler front-end. Important limitations include:

- no GitHub network/auth adapter yet; GitHub can be materialized externally and analyzed through the source contract;
- no framework-specific AST parser or route manifest reader;
- import alias resolution (`@/`, tsconfig paths, webpack aliases) is not resolved yet;
- Python absolute imports are resolved only when they match indexed paths directly;
- dynamic imports/metaprogramming may be missed;
- semantic classifier is deterministic; no LLM provider is wired into Project Intelligence yet;
- behavioral facts are static signals and do not prove runtime reachability.

These limitations must be surfaced rather than compensated for with guesses.

## Relationship to later QGate stages

Project Intelligence answers: **What does this project contain, how is it connected, and what meaningful code states/signals are visible?**

Impact Analysis will answer: **What could this specific change affect?**

Scenario Intelligence will answer: **Which realistic states should we test?**

Suitest/Playwright will answer: **What actually happens at runtime?**

QA Memory and Final Gate will use the resulting evidence to make durable regression knowledge and PASS/BLOCK/MANUAL REVIEW decisions.
