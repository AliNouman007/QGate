# Impact Analysis V1 Design

## Purpose

Impact Analysis V1 determines the realistic blast radius of a code change by combining deterministic diff facts with the existing merged `ProjectKnowledge` produced by Project Intelligence. It must not behave like a generic AI PR reviewer and must not make unsupported impact claims.

## Product workflow

Input change source
→ normalize into `ChangeSet`
→ map changed files/lines/symbols into `ProjectKnowledge`
→ traverse direct/reverse dependency relationships
→ identify affected routes/components/shared modules
→ link relevant behavioral and semantic states
→ classify impact level and confidence
→ optionally enrich bounded impact evidence with AI
→ produce structured `ImpactReport`
→ expose concise CLI/API/dashboard views for developers
→ feed the structured report into future Scenario Intelligence

## Core principles

1. The diff is the source of truth for what changed.
2. Project Intelligence is the source of truth for known project structure, routes, symbols, dependencies, framework facts, behavioral facts, and semantic states.
3. Graph traversal is the primary mechanism for blast-radius discovery.
4. AI is optional and bounded; it may explain, group, or prioritize evidence-backed impacts but may not invent relationships or overwrite deterministic evidence.
5. Every claimed impact must carry reason, evidence, confidence, and impact level.
6. Unsupported or runtime-dependent relationships must be represented as unknown/possible rather than guessed.
7. Impact Analysis must consume the existing `ProjectKnowledge` contract and must not create a second code-understanding engine.
8. Scenario generation is explicitly out of scope for this PR.

## Scope

Impact Analysis V1 is one complete feature PR and includes:

- structured `ChangeSet` models;
- local Git diff source;
- supplied unified diff/patch source;
- GitHub PR change-source adapter where the current QGate connector/runtime can provide PR metadata and patch content cleanly;
- changed-file and changed-line parsing;
- changed-symbol matching against Project Intelligence symbols/evidence;
- change-type classification;
- forward/reverse dependency tracing;
- shared-module/component blast-radius analysis;
- affected route discovery;
- affected behavioral/semantic state discovery;
- direct vs indirect vs possible vs unknown impact levels;
- evidence, reason, confidence, and runtime-verification flags;
- bounded optional AI enrichment through the existing `LLMProvider` boundary;
- structured `ImpactReport` suitable for Scenario Intelligence;
- CLI output;
- local read-only API;
- developer-facing Impact dashboard view;
- unit/integration/web tests;
- `docs/IMPACT_ANALYSIS.md` plus any required API/docs updates.

## Change source abstraction

Impact Analysis should use a transport-independent `ChangeSource` contract so the engine does not depend on GitHub.

Normalized output: `ChangeSet`.

A `ChangeSet` should contain at minimum:

- source kind;
- base/head identifiers when known;
- changed files;
- file status (`added`, `modified`, `deleted`, `renamed` where supported);
- changed line ranges/hunks;
- added/removed line counts;
- raw hunk evidence or bounded excerpts;
- optional PR/branch metadata.

Initial sources:

### Local Git source

Reads a user-supplied repository path and compares refs such as `main...HEAD` without modifying the target repository. It should use Git commands as the canonical diff mechanism and fail clearly when the path is not a Git repository or refs cannot be resolved.

### Unified diff/patch source

Parses supplied unified diff text/file into the same `ChangeSet` schema. It should support normal Git-style patches and record coverage gaps for unsupported/ambiguous constructs rather than silently misparse them.

### GitHub PR source

Where available, GitHub PR metadata/patch is normalized into the same `ChangeSet`. GitHub transport/auth logic must remain outside the core impact engine. The engine must work without GitHub.

## Changed symbol mapping

Changed hunks should be mapped to Project Intelligence evidence/symbols conservatively.

Priority order:

1. exact changed file path;
2. symbol whose evidence line overlaps or is near the changed hunk;
3. file-level impact if symbol resolution is unavailable;
4. unknown mapping when evidence is insufficient.

Impact Analysis must never fabricate a changed symbol solely from a line string.

## Change classification

Each changed file/hunk may receive one or more evidence-backed categories such as:

- UI/rendering;
- styling/CSS;
- state/conditional behavior;
- routing/navigation;
- API/data access;
- auth/permission;
- feature flag/experiment;
- storage/session;
- responsive behavior;
- shared component/module;
- configuration/build/tooling;
- test-only;
- general/unknown.

Classification should be deterministic first, using file role, framework facts, behavioral facts, paths/extensions, and changed-line signals. Optional AI may improve human-readable grouping but cannot replace the deterministic category evidence.

## Blast-radius engine

The engine starts from changed project nodes and traverses the existing dependency graph.

### Direct impact

Includes:

- changed files/symbols themselves;
- routes/components directly represented by the changed file;
- behavioral/semantic states whose evidence is in the changed file/hunk.

### Indirect impact

Includes reverse dependents/importers of changed modules and components. Traversal is bounded by configurable depth/node limits to remain predictable on large projects.

Each indirect item records the dependency path that explains why it was included.

### Shared/reused impact

If a changed component/module has multiple importers, the report should explicitly expose reuse count and affected surfaces/routes rather than presenting each importer as an unrelated finding.

### Route impact

Routes are derived from:

- changed route files;
- routes/components that depend on changed shared code;
- dependency paths connecting a changed module to route-owning files.

### State impact

Relevant states are derived from:

- behavioral facts in changed files;
- semantic states whose evidence is in changed files;
- states attached to impacted dependent files/components when the dependency path is strong enough;
- otherwise marked possible/runtime-verification-required rather than definite.

## Impact levels

Every `ImpactItem` uses one of:

- `DIRECT` — changed code itself or exact evidence overlap;
- `INDIRECT` — deterministic dependency/reuse path from changed code;
- `POSSIBLE` — evidence suggests relevance but runtime/semantic confirmation is needed;
- `UNKNOWN` — insufficient static evidence to determine blast radius.

Impact level is separate from risk/severity. V1 should avoid pretending to know business severity without evidence.

## Confidence and evidence

Every impact item must include:

- stable key/id;
- target type (file, symbol, component, route, state, module, etc.);
- target name/path;
- impact level;
- reason;
- confidence (`high`, `medium`, `low`);
- supporting source evidence;
- dependency path where relevant;
- change categories;
- `needs_runtime_verification` where static evidence is insufficient.

High confidence should require deterministic direct or graph evidence. AI may not raise confidence above the deterministic support level.

## AI enrichment boundary

AI is optional and consumes bounded `ImpactEvidencePack` objects, never the full repository or unrestricted PR.

The pack may contain:

- one or a small group of deterministic changed-file facts;
- relevant changed-line excerpts;
- Project Intelligence symbol/route/state facts;
- dependency path;
- deterministic impact classification.

AI may return:

- clearer human-facing explanation;
- grouping label;
- priority hint for later Scenario Intelligence;
- runtime-verification recommendation.

AI may not:

- add unsupported affected files/routes/states;
- replace evidence;
- remove an existing runtime-verification requirement without deterministic proof;
- raise confidence above deterministic support.

Malformed/provider failure falls back to the deterministic report.

## Structured output

`ImpactReport` should contain:

- report/schema/analyzer versions;
- source/change metadata;
- ProjectKnowledge fingerprint used;
- summary counts;
- changed files and changed symbols;
- direct impacts;
- indirect impacts;
- affected routes;
- affected states;
- shared/reused blast-radius groups;
- unknown/coverage gaps;
- optional AI-enriched explanations/priority hints;
- runtime-verification requirements.

This structured report is the contract future Scenario Intelligence consumes.

## Persistence

Impact reports should be stored in QGate-owned storage, separate from the analyzed target repository. Reports should include the change identity and ProjectKnowledge fingerprint so stale reports can be detected.

## CLI

A concise developer flow should support at least:

- local Git comparison against a base ref;
- supplied diff/patch input;
- explicit ProjectKnowledge file/store selection when needed;
- structured JSON output;
- human-readable Impact Report output.

The CLI should fail clearly when ProjectKnowledge is missing/stale enough that reliable analysis cannot be performed.

## API and dashboard

Local mode should expose read-only Impact Analysis results through normal QGate authentication, similar to Project Map.

The dashboard should provide an Impact view that answers quickly:

- what changed;
- direct impact;
- indirect/shared blast radius;
- affected routes;
- affected states;
- why each item is included;
- confidence;
- runtime-verification warnings;
- unknown/coverage gaps.

The browser must not be allowed to submit arbitrary filesystem paths to the read API. Analysis remains a local/controlled operation; the UI reads persisted reports.

## Error handling and safety

- Missing ProjectKnowledge → explicit error/manual requirement, not guessed impact.
- ProjectKnowledge source/fingerprint mismatch → surface stale/mismatch warning or fail according to severity.
- Deleted file → preserve change fact; dependency/state mapping may use previous ProjectKnowledge where available.
- Renames → preserve old/new path when diff source supports it.
- Unresolved import/dynamic dependency → coverage gap/possible impact.
- Traversal limits exceeded → coverage gap and runtime/manual verification requirement.
- Unsupported patch syntax → parse gap/failure, never silently discard affected hunks.
- Target repository remains read-only.

## Testing strategy

### Unit tests

- unified diff parsing;
- local Git ChangeSet normalization;
- changed-line range parsing;
- symbol overlap mapping;
- deterministic change classification;
- direct/indirect impact levels;
- reverse dependency traversal;
- traversal bounds/cycle handling;
- route impact discovery;
- state impact discovery;
- confidence/evidence rules;
- stale/missing knowledge behavior;
- AI confidence/evidence guardrails and fallback.

### Integration tests

Temporary React/Next/TypeScript fixture repository:

- build ProjectKnowledge;
- commit baseline;
- modify shared component;
- analyze Git diff;
- verify direct changed component;
- verify multiple reverse dependents;
- verify affected routes;
- verify relevant states;
- verify unrelated routes are not included;
- verify shared-component grouping;
- verify report persistence/reload.

Additional fixtures should test styling-only changes, route changes, auth/state conditions, file deletion/rename where feasible, and unknown/dynamic dependencies.

### API/web tests

- empty report state;
- latest/list/detail report reads;
- local-only API behavior;
- auth preservation;
- Impact dashboard direct/indirect/routes/states/unknown rendering;
- production web build/typecheck.

## Success criteria

Impact Analysis V1 is complete when a realistic frontend change such as editing a reused React component can produce an evidence-backed report that correctly identifies:

1. the changed file/symbol;
2. direct impact;
3. reverse dependents/shared reuse;
4. affected routes;
5. relevant behavioral/semantic states;
6. unknown/runtime-dependent impact separately;
7. why each impact exists;
8. confidence/evidence for every claim;
9. no unrelated routes/components in the tested fixture;
10. a stable structured report that Scenario Intelligence can consume.

## Non-goals

- generating Playwright scenarios;
- executing browser tests;
- deciding PASS/BLOCK/MANUAL REVIEW REQUIRED;
- learning historical QA findings;
- automatic production-code fixes;
- rebuilding Project Intelligence parsing inside Impact Analysis;
- whole-repo or whole-PR LLM prompting.
