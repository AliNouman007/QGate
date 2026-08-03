# Testing approaches and QA mindset

> **Build status: implemented.** The lifecycle, API, database, MCP tools, publish
> path, and web UI support the contracts in this document.

Suitest treats a testing approach and a test level as separate dimensions.
`BLACK_BOX`, `GRAY_BOX`, and `WHITE_BOX` describe what the tester can observe;
`UNIT`, `COMPONENT`, `INTEGRATION`, `SYSTEM`, and `E2E` describe test scope.

## Selection

`testing.approach` accepts `auto`, `black-box`, `gray-box`, or `white-box`.

- `auto` + repository analysis resolves to `GRAY_BOX`.
- `auto` + OpenAPI, Postman, crawl, or live UI analysis resolves to `BLACK_BOX`.
- `WHITE_BOX` is explicit and requires a compatible local test provider.
- A suite may define `default_testing_approach`; a case may override it.
- The effective case value is: case override → suite default → `BLACK_BOX`.

This prevents source availability from silently turning every test into a
black-box test and prevents repository access from silently claiming
white-box coverage.

## Risk-based strategy

Every generation writes a deterministic strategy before execution:

```text
suitest-output/
└── backend|frontend/
    ├── standard_prd.json
    ├── suitest_<mode>_test_strategy.json
    ├── suitest_<mode>_test_plan.json
    ├── TC001_...
    ├── tmp/
    ├── tcm/
    └── reports/
```

No approach-specific directory is introduced. Each case and result carries
`testingApproach`, `testLevel`, `framework`, and `strategyRef`.

The strategy records access signals, risks, failure modes, assumptions,
oracles, coverage dimensions, exclusions, and QA checks. ZERO creates the
baseline deterministically. LOCAL/CLOUD may enrich a draft through
`packages/agent`; a human must approve a version before it becomes the
project's approved strategy.

The QA checks implement the product's testing posture:

- question unstated assumptions;
- prioritize impact and likelihood over case count;
- require an observable oracle for every case;
- include negative, boundary, permission, state, concurrency, dependency,
  recovery, and accessibility risks where relevant;
- reject duplicate or brittle assertions;
- record exclusions and remaining risk.

## White-box provider contract

The local contract is `suitest.whitebox.v1`. Built-in reference adapters:

- `pytest`;
- `vitest`;
- `jest`.

Adapters discover native test files, execute each target without a shell,
copy the native source into the normal `TCxxx` output, normalize coverage.py
or Istanbul JSON, and publish through the existing lifecycle ingest path.
Coverage thresholds remain owned by the repository configuration; Suitest
does not impose a universal percentage.

Example:

```json
{
  "mode": "backend",
  "projectName": "example",
  "projectPath": ".",
  "baseUrl": "http://localhost",
  "server": { "autostart": false },
  "testing": {
    "approach": "white-box",
    "level": "UNIT",
    "framework": "pytest",
    "coverageFile": "coverage.json"
  },
  "output": "suitest-output"
}
```

Run it with `suitest test --config suitest.config.json`. MCP clients can use
`whitebox_discover_tests` and `whitebox_run_tests` with the same config.

## Publishing

The existing `PublishSession` remains authoritative. It imports case metadata
and native automation source, streams results, uploads coverage as an artifact,
and stores the normalized coverage summary on the run. The web UI exposes
approach badges and filters, case overrides, strategy review/approval, native
code, and run coverage.
