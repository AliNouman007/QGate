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
11. human-readable project map and CLI.

V1 does not require cloud or local LLM access. Future LLM enrichment must consume bounded evidence packs through the semantic-classifier interface and may never receive an unrestricted whole-repository dump.

## Architecture

A new workspace package, `qgate-project-intelligence`, owns Project Intelligence. Keeping it in a dedicated package isolates code-understanding responsibilities from Suitest execution, MCP, DB, and agent packages.

Data flow:

`ProjectSource -> ProjectScanner -> per-file analysis -> dependency graph -> semantic classification -> ProjectKnowledge -> JsonKnowledgeStore / report`

Incremental flow:

`previous ProjectKnowledge + current source -> compare file hashes -> reuse unchanged FileAnalysis -> re-analyze changed/new files -> drop removed files -> rebuild graph/summary -> persist new knowledge`

## Source adapters

`ProjectSource` exposes a stable `root` and `iter_files()` contract. `LocalPathSource` analyzes an existing directory without modifying it. `ZipProjectSource` extracts an archive into a temporary directory owned by the adapter and cleans it up after analysis. Transport-specific adapters such as GitHub can be added later without changing the scanner.

## Bounded scanning

`AnalysisBudget` limits maximum discovered files, bytes read per file, total source bytes, and directory depth. Default ignored directories include VCS metadata, dependencies, build outputs, caches, virtual environments, and generated coverage artifacts. When a budget or unsupported binary/encoding construct prevents analysis, the knowledge output records a coverage gap rather than silently omitting it.

## Static facts and evidence

Every file gets a `FileAnalysis` containing basic metadata, import facts, behavioral condition facts, and evidence references. Evidence contains the relative path, line number, excerpt, and fact kind. Structural graph edges reference evidence where available.

Regex/line parsing is intentionally conservative in V1. It supports common import forms and recognizable conditions but records coverage gaps for unsupported constructs. Future AST parsers can replace internal extractors without changing the public models.

## Behavioral classification

A condition is not automatically a QA state. V1 tags conditions with categories such as `auth`, `permission`, `feature_flag`, `loading`, `error`, `empty`, `storage`, `responsive`, `general`, or `technical_guard`. Heuristics use variable names, operators, early-return patterns, and surrounding text. Confidence is explicit (`high`, `medium`, `low`) and uncertain facts remain facts rather than being promoted to guaranteed states.

## Semantic classification contract

`SemanticClassifier` accepts only a bounded `EvidencePack` built from deterministic facts. `HeuristicSemanticClassifier` provides a no-LLM implementation for V1. A future agent-backed implementation may enrich names/grouping/explanations but must preserve evidence references and confidence and must mark uncertainty instead of inventing facts.

## Persistence

`JsonKnowledgeStore` writes knowledge under a caller-supplied QGate data directory, never inside the target project. Each project has a stable storage key derived from source identity. Stored metadata includes schema version, analyzer version, timestamp, source fingerprint, and per-file hashes.

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
- ZIP ingestion;
- persistence outside the target repo;
- incremental reuse when only one file changes;
- human-readable report generation.

The package must be added to the uv workspace, mypy path, and default pytest testpaths.

## Documentation

`docs/PROJECT_INTELLIGENCE.md` is the subsystem documentation. `docs/README.md` links to it. `QGATE_PROGRESS.md` is updated on the feature branch to reflect implemented V1 capabilities; the progress becomes canonical only when the PR is merged.

## Safety and non-goals

- Never modify the analyzed target project.
- Never require the target project to install QGate dependencies.
- No whole-repo LLM prompts.
- No framework-specific marketplace behavior.
- No automatic test generation or final QA decision in this phase.
- No unrelated Suitest refactor.
