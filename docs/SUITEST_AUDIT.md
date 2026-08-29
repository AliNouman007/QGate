# Suitest → QGate Audit

## Goal
Use Suitest as QGate's testing/runtime foundation, while adding QGate-specific intelligence for a developer-owned pre-PR QA gate.

## Keep (high value for QGate)
- `apps/web` — browser dashboard / reporting UI
- `apps/api` — local API/backend
- `apps/runner` — deterministic execution worker
- `packages/mcp` — MCP plugin/runtime layer
- Playwright/browser automation integration
- Black-box discovery and interaction graph features
- Test case/run management
- Evidence collection: screenshots, video, logs, failure context
- `packages/agent` provider abstraction / LiteLLM routing where useful
- GitHub integration primitives
- Auth and local workspace/project concepts, simplified later if needed

## Keep initially, then simplify only after QGate works
- Postgres/DB models
- Redis job queue
- artifact storage abstraction
- capability tiers
- runner isolation/sandboxing
- realtime run logs

Removing these too early risks breaking a working foundation.

## Likely not needed for QGate V1
These should NOT be deleted immediately. First prove they are not dependencies, then remove behind a dedicated cleanup branch.
- Jira integration
- Linear integration
- Slack notifications
- GitLab integration
- Kubernetes/Helm deployment support
- enterprise-scale autoscaling/HPA configuration
- broad backend/API/database testing features not used by the marketplace workflow
- Appium/mobile-native functionality if present/added upstream
- upstream release/publishing automation specific to maintaining Suitest itself
- contributor/community files that are irrelevant to a private internal fork, except required license/NOTICE attribution

## QGate intelligence to add

### 1. Project Intelligence
Build a persistent behavioral model of the target frontend repository:
- component/import/usage graph
- route graph
- parent/child UI relationships
- conditions and conditional rendering
- auth/user states
- cookies/feature flags
- state-management selectors
- API/data fields that affect UI
- responsive breakpoints
- known high-risk areas (Checkout/Cart, Product Cards/PLP, PDP first)

Output: structured project knowledge graph/state graph used by all later QGate modules.

### 2. Impact Analysis
For a PR/branch diff:
- classify change type (visual, state, business logic, API/data, routing, shared component)
- trace direct dependencies
- trace indirect usage/blast radius
- identify affected flows/pages/states
- attach evidence for each claimed impact
- rank relevance without confusing theoretical reachability with real product states

Output: evidence-backed Impact Report.

### 3. Scenario Intelligence
Turn project knowledge + impact report + historical QA knowledge into testable scenarios:
- discover meaningful state combinations automatically
- separate reachable/likely states from theoretical states
- generate focused E2E/browser scenarios
- promote confirmed useful scenarios into permanent regression coverage
- support both change-focused QA and broader project exploration

### 4. QA Memory
Persist marketplace-specific learning:
- human QA revisions
- confirmed product rules
- historical bug patterns
- fragile components/states
- promoted regression scenarios
- false-positive patterns / unreachable states

Memory must support provenance: who/what confirmed a rule and from which run/change.

### 5. Final Gate
Evidence-based final decision only:
- `PASS`
- `BLOCK`
- `MANUAL REVIEW REQUIRED`

Rules:
- important untested scenario => PASS forbidden
- environment/auth/setup failure != product bug
- high-confidence BLOCK should reference runtime/code evidence
- AI speculation alone cannot produce a confident PASS

## Proposed QGate flow

Target repo / PR
→ Project Intelligence
→ Impact Analysis
→ Scenario Intelligence
→ Suitest runner / MCP / Playwright
→ runtime evidence
→ QA Judge + QA Memory
→ PASS / BLOCK / MANUAL REVIEW

## Architecture stance
- Keep Suitest as the execution/platform foundation.
- Add QGate intelligence as clearly separated modules first.
- Do not rewrite the working runner/dashboard/MCP stack unless a concrete limitation is proven.
- Prefer a monorepo/monolith-first development model while QGate is still one local product.
- Keep QGate local/private and avoid modifying the company repository.

## License note
Suitest is Apache-2.0 licensed. Preserve upstream LICENSE/NOTICE and attribution requirements when importing/modifying the source.
