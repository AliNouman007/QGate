# Impact Analysis

Impact Analysis is QGate's change-understanding layer. Project Intelligence answers what the project contains and how it is connected; Impact Analysis answers what a specific code change can affect and why.

## Business workflow

A developer supplies either a local Git comparison, a unified diff/patch, or GitHub PR patch content through an adapter. QGate normalizes that input into a `ChangeSet`, then combines the exact changed files/hunks with the previously generated `ProjectKnowledge`.

The V1 flow is:

`Git diff / patch -> ChangeSet -> changed-file/symbol mapping -> reverse dependency traversal -> routes/states/shared reuse -> ImpactReport -> QGate-owned store -> API -> Impact dashboard`

The diff is the source of truth for **what changed**. Project Intelligence is the source of truth for known project structure, dependencies, routes, components, behaviors, and semantic states. AI is optional and may only explain or prioritize impacts already supported by deterministic evidence.

## Code ownership

Core Impact Analysis lives in:

`packages/impact-analysis/`

Important modules:

- `models.py` — ChangeSet, ImpactReport, impact levels/categories, evidence and metadata contracts.
- `diff_parser.py` — conservative Git-style unified diff parsing.
- `source.py` — local Git, supplied patch, and transport-neutral GitHub patch sources.
- `mapping.py` — changed-hunk to Project Intelligence symbol mapping.
- `classifier.py` — deterministic change categories.
- `engine.py` — bounded reverse dependency traversal and blast-radius analysis.
- `semantic.py` — bounded evidence packs for optional AI enrichment.
- `store.py` — JSON report persistence in QGate-owned storage.
- `report.py` — concise developer-facing text report.
- `cli.py` — local Git/patch command-line entrypoint.

Optional AI enrichment lives in:

`packages/agent/src/suitest_agent/impact_analysis_semantic.py`

Dashboard/API integration lives in:

- `apps/api/src/suitest_api/routers/impact_analysis.py`
- `apps/web/src/hooks/use-impact-analysis.ts`
- `apps/web/src/routes/_app/impact.tsx`

## Inputs

### Local Git comparison

`LocalGitSource` executes read-only Git commands against a supplied repository path. It validates the requested refs and uses a merge-base-style comparison such as `main...HEAD`. It never checks out files, commits, stages, or modifies the target repository.

### Unified diff / patch

`UnifiedDiffSource` accepts Git-style unified diff text or a patch file. V1 recognizes modified, added, deleted, and rename metadata plus hunk ranges and bounded excerpts. Unsupported or malformed hunks become explicit gaps rather than silently disappearing.

### GitHub PR

`GitHubPatchSource` normalizes patch text and PR metadata already fetched by a GitHub connector into the same `ChangeSet`. Authentication/network transport remains outside the core analyzer, so Impact Analysis is not coupled to GitHub and can run fully locally.

## ChangeSet

A normalized `ChangeSet` records:

- source kind and identity;
- base/head refs when known;
- changed files;
- add/modify/delete/rename status;
- old path for renames where available;
- changed old/new line ranges;
- bounded hunk evidence;
- additions/deletions;
- parsing gaps.

This normalized contract lets all change sources use the same impact engine.

## Changed symbol mapping

V1 maps a change to known symbols conservatively:

1. exact changed file path must exist in ProjectKnowledge;
2. a Project Intelligence symbol's evidence line must overlap or be near a changed hunk;
3. if no symbol can be proven, the file remains directly changed without inventing a symbol;
4. a changed file missing from ProjectKnowledge receives an `UNKNOWN` mapping requiring verification.

A symbol name is never fabricated from arbitrary diff text.

## Change categories

Deterministic classification uses Project Intelligence facts plus changed path/hunk signals. Categories include:

- UI/rendering;
- styling;
- state/conditional behavior;
- routing/navigation;
- API/data access;
- auth/permission;
- feature flag/experiment;
- storage/session;
- responsive behavior;
- shared/reused component/module;
- configuration/tooling;
- test-only;
- general.

A reused changed module is explicitly marked `shared` when Project Intelligence has evidence of multiple known importers.

## Blast-radius analysis

### Direct impact

A directly changed file is always a `DIRECT` impact. Known symbols whose source evidence overlaps or is close to a changed hunk can also be direct impacts.

A route declared by a changed route file is direct. A semantic state is direct only when its evidence overlaps or is adjacent to the changed hunk; merely living somewhere else in the same file is not enough.

### Indirect impact

The engine walks the existing Project Intelligence dependency graph **backwards** from changed code to its importers/dependents. This is the main deterministic blast-radius technique.

Traversal is:

- cycle-safe;
- limited by maximum depth;
- limited by maximum visited nodes;
- evidence-backed with the dependency path that caused inclusion.

If a limit is reached, QGate records a coverage gap instead of pretending analysis is complete.

### Shared/reused impact

When a changed module has multiple known importers, Impact Analysis groups the reuse count, affected dependent files, and affected routes. This makes a shared component change visibly different from an isolated file edit.

### Routes

Affected routes come from route-owning files that are either directly changed or deterministically depend on changed code. Unrelated routes with no dependency path are not included.

### States

Semantic states whose evidence overlaps a changed hunk may be direct. States associated only with dependent code—or with another part of the changed file—are reported as `POSSIBLE` and require runtime verification because static analysis cannot prove that the change actually alters that state at runtime.

## Impact levels

Each `ImpactItem` has one level:

- `DIRECT` — exact changed code or evidence overlap.
- `INDIRECT` — deterministic dependency/reuse path from changed code.
- `POSSIBLE` — relevant static evidence exists, but runtime relevance/reachability is not proven.
- `UNKNOWN` — QGate lacks enough structural evidence to determine blast radius.

Impact level is deliberately separate from business severity. V1 does not guess whether an impact is P0/P1 or user-critical without evidence.

## Evidence and confidence

Every impact item contains:

- stable key;
- target type/name;
- impact level;
- reason;
- confidence;
- source evidence;
- dependency path where applicable;
- change categories;
- runtime-verification flag;
- optional AI explanation/priority hint.

High confidence requires deterministic evidence. Unsupported relationships are never upgraded just because an LLM suggests them.

## Optional AI enrichment

`build_impact_evidence_packs` produces small, bounded, deduplicated packs from already-determined impact items. The agent-layer `enrich_impact_report` can send these packs through the existing provider-independent `LLMProvider` contract.

AI may improve:

- human-facing explanation;
- grouping/priority hint;
- recommendation that runtime verification is needed.

AI may **not**:

- create a new impacted file, route, state, component, or relationship;
- replace deterministic source evidence;
- raise confidence above deterministic confidence;
- turn an existing runtime-verification requirement off;
- receive the unrestricted repository or whole PR.

Unknown returned keys are ignored. Invalid provider output safely leaves the deterministic report unchanged.

## ImpactReport

The structured `ImpactReport` contains:

- schema/analyzer metadata;
- ProjectKnowledge source/fingerprint used;
- change-source identity;
- normalized ChangeSet;
- changed symbols;
- direct, indirect, possible, and unknown impacts;
- affected routes;
- affected states;
- shared/reused groups;
- coverage gaps;
- summary/runtime-verification counts.

This structured model—not the prose dashboard—is the contract that future Scenario Intelligence will consume.

## Persistence

Impact reports are stored outside target repositories. Default CLI location:

`~/.qgate/impact-analysis`

The API uses `SUITEST_IMPACT_ANALYSIS_DIR`, with the same default. A stable 24-character report key is derived from project identity, ProjectKnowledge fingerprint, and change identity.

## CLI

Analyze a local feature branch against main:

```bash
qgate-impact-analysis git /path/to/project \
  --base main \
  --head HEAD \
  --knowledge /path/to/project-knowledge.json
```

Analyze a supplied patch:

```bash
qgate-impact-analysis patch /path/to/change.patch \
  --knowledge /path/to/project-knowledge.json
```

Add `--json` for structured output. `--max-depth` and `--max-nodes` bound reverse traversal. `--store-dir` changes the QGate-owned persistence location.

For local Git analysis, the ProjectKnowledge source identity must match the supplied repository path. If it does not, the CLI fails explicitly instead of combining unrelated project knowledge with a diff.

## Local API

The dashboard read model is available only when `SUITEST_MODE=local` and preserves normal workspace authentication:

- `GET /api/v1/impact-analysis/reports`
- `GET /api/v1/impact-analysis/latest`
- `GET /api/v1/impact-analysis/reports/{key}`

The API is read-only. The browser cannot submit filesystem paths or trigger arbitrary Git operations through these endpoints.

## Impact dashboard

The `/impact` dashboard shows the latest persisted report, including:

- changed files and change categories;
- changed symbols;
- direct impact;
- indirect/shared blast radius;
- affected routes;
- affected states;
- possible/unknown impact;
- confidence and reasons;
- dependency paths;
- runtime-verification warnings;
- coverage gaps.

An empty local store displays `No impact report yet` rather than an application failure.

## Safety and limitations

Impact Analysis V1 deliberately remains conservative:

- ProjectKnowledge should be generated from the same target project and should be refreshed when materially stale. V1 can validate local source identity but cannot cryptographically prove that an arbitrary patch was produced from the exact knowledge snapshot.
- Dependency quality is bounded by Project Intelligence. Unsupported TypeScript aliases, dynamic imports, generated wiring, or runtime dependency injection may become gaps or remain unknown.
- Changed symbol mapping is line/evidence based, not a compiler-level AST diff.
- Static dependency reachability does not prove that a user can reach the affected runtime state.
- GitHub network/auth fetching is handled by a connector outside this core package; `GitHubPatchSource` consumes already-fetched patch content.
- Traversal limits intentionally trade completeness for predictable behavior on large projects; hitting a bound creates a manual/runtime-verification gap.

These limitations are expected inputs to later Scenario Intelligence and browser verification, not reasons to invent certainty.

## Testing

The V1 test set covers:

- unified diff normalization including add/delete/rename;
- local Git read-only comparison;
- changed symbol mapping;
- direct/indirect blast radius;
- cycle/bounds handling;
- shared component reuse;
- affected routes with unrelated-route exclusion;
- affected state handling;
- unknown files;
- report persistence/rendering;
- bounded AI guardrails/fallback;
- local API behavior;
- dashboard empty/populated views;
- realistic React/Next.js/TypeScript Git fixture integration.

Local verification must also regenerate the uv lockfile and TanStack route tree, run static checks/builds, and visually smoke-test the dashboard before merge.

## Relationship to the next QGate stage

Project Intelligence answers: **What does this project contain and how is it connected?**

Impact Analysis answers: **What could this specific code change affect, and why?**

Scenario Intelligence will answer: **Given those impacts, which realistic states and user flows should QGate actually test?**

Suitest/Playwright will then verify those scenarios at runtime and collect evidence for later QA Memory and Final Gate decisions.
