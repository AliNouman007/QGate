# Desktop Testing (M14) — Design & slint-mcp Contract

> Cross-links: [MCP_PLUGINS.md](./MCP_PLUGINS.md), [ROADMAP.md](./ROADMAP.md),
> [DATA_MODEL.md](./DATA_MODEL.md), [DEPLOYMENT.md](./DEPLOYMENT.md),
> [ARCHITECTURE.md](./ARCHITECTURE.md), [BLACKBOX_UI_TESTING.md](./BLACKBOX_UI_TESTING.md).
>
> Companion example: [`examples/slint-demo/`](../examples/slint-demo/).

This doc defines the **M14 desktop-testing milestone** (M14-1 .. M14-3) and the
**slint-mcp wire contract** that any external runner binary must implement so a
Slint desktop app can be automated the way Playwright automates the browser DOM.

---

## 1. Goal & non-goals

**Goal.** Let a Suitest case target a *desktop* application (`target_kind =
FE_DESKTOP`) and drive it with typed MCP tools — click, type, read state,
assert text/visibility/value — exactly as browser steps drive the DOM.

**Non-goals (this milestone).**
- No OS-level window automation of *arbitrary* native apps (covered by M14-1
  computer-use for screen-level fallback).
- No modification of the target app's source. The driver speaks to the running
  app through Slint's accessibility surface; instrumentation hooks are optional
  and opt-in (see [§4.2](#42-property-bridge-os-and-slint-only)).
- No bundling of the external runner binaries into the Suitest image.

---

## 2. Three backends (M14-1 .. M14-3)

Desktop automation is not one problem; it is three. Suitest ships **three
provider configs** in `builtin_specs.py`, all resolved at runtime via
`command_pin` (binaries stay **outside the image** — see
[DEPLOYMENT.md](./DEPLOYMENT.md)).

| ID | M14 item | Driver | Transport | Best for |
|----|----------|--------|-----------|----------|
| `computer-use-mcp` | **M14-1** | Screen pixels + OS input | stdio | Any legacy/native app; last-resort fallback |
| `electron-mcp` | **M14-2** | Chrome DevTools Protocol inside Electron (Playwright `_electron`) | stdio | Electron apps with real DOM |
| `slint-mcp` | **M14-3** | Slint **accessible tree** | stdio | Slint apps (Rust, cross-platform, optionally headless) |

### 2.1 Routing & default

`routing.py` maps `TargetKind.FE_DESKTOP` to `computer-use-mcp` as the default.
Steps that need structure pin a more specific provider:

```python
DEFAULT_ROUTING = {
    ...
    TargetKind.FE_DESKTOP: ("computer-use-mcp", None),  # default = screen-level
}
```

- `computer-use-mcp` is the FE_DESKTOP default (it works on *anything*).
- `electron-mcp` / `slint-mcp` are chosen per step when a structural driver is
  available — same selector grammar, better fidelity, faster, headless-capable.

### 2.2 Residency rule (command_pin)

None of the three desktop binaries are shipped in the image. `command_pin`
maps the logical command name (`computer-use-mcp`, `electron-mcp`,
`slint-mcp`) to an absolute host binary supplied by the operator/CI runner, so:
- the image stays thin and the executor host owns its binaries/versions;
- no native GUI/Chrome/OS-API deps leak into the Suitest image;
- `examples/slint-demo` and tests never reach into the `rdb` repo (that repo is
  a *sample target only* and is not modified).

---

## 3. slint-mcp: selector grammar

`slint-mcp` drives the app through Slint's **accessible tree** — the same
semantics used by screen readers — so no browser DOM and (with the software
renderer) no display server are required.

Selectors are JSON objects. Priority when resolving:

1. `accessible-id` (most explicit; the Slint equivalent of `data-testid`)
2. `accessible-label` + `accessible-role` (stable, human-friendly)

```jsonc
// by accessible-id
{ "id": "btn-submit" }
// CSS-ish shorthand accepted by the runner for convenience
"[id=\"btn-submit\"]"

// by label + role pair
{ "label": "Submit", "role": "button" }
// role-only for uniqueness within a container
{ "role": "button", "container": "login-form" }
```

### 3.1 Tagging in the `.slint` source

The example screen tags every interactive element via Slint's accessibility
properties (rendered by the compiler into the accessible tree):

```slint
Button {
    accessible-id: "btn-submit";
    accessible-label: "Submit";
    text: "Submit";
}
```

Supported roles that Suitest's assertions recognise: `button`, `check box`,
`text input`, `text`, `heading`, `radio button`, `slider`, `combo box`,
`list`, `table`. Unknown roles degrade to a generic node with an `id`.

---

## 4. slint-mcp tool contract

The runner exposes a standard MCP server (stdio transport) with `tools/list`
describing the catalog below. Suitest's `invoker` calls them through the normal
`mcp` client; every tool returns a structured JSON result and
`suitest_output`/`call_timeout` semantics.

### 4.1 Lifecycle

| Tool | Params | Returns / effect |
|------|--------|------------------|
| `slint.launch` | `path` (`.slint` or app binary), `args?`, `headless?` (default true) | 200-style `{ ok, pid, root }`; mounts the UI tree |
| `slint.close` | — | tears down the instance |

### 4.2 Property bridge (OS + Slint only)

| Tool | Params | Returns / effect |
|------|--------|------------------|
| `slint.get_property` | `selector`, `property?` | current value of the resolved element (text / checked / value) |
| `slint.set_property` | `selector`, `value`, `property?` | writes the value |
| `slint.click` | `selector` | dispatches `accessible-action-default()` on the element |
| `slint.type_text` | `selector`, `text`, `clear?` | sets text-input content (focused) |
| `slint.check` / `slint.uncheck` | `selector` | toggles a check box |

> The **property bridge touches only the OS+Slint surface**: Slint properties
> you expose explicitly (e.g. `out property <string> status-text`) plus
> OS-level signals (focus, geometry). It does **not** read arbitrary app state,
> keeping the driver decoupled from app internals — same philosophy as
> `accessible-id` after compile.

### 4.3 Assertions

| Tool | Params | Pass condition |
|------|--------|----------------|
| `slint.assert_visible` | `selector`, `equals` (bool) | element present (and, if given, visible) |
| `slint.assert_text` | `selector`, `equals` | resolved text equals string |
| `slint.assert_checked` | `selector`, `equals` (bool) | check box state equals bool |
| `slint.assert_value` | `selector`, `equals` | numeric/label value equals |

### 4.4 Diagnostics

| Tool | Params | Returns |
|------|--------|---------|
| `slint.screenshot` | `selector?` | base64 PNG of window / element |
| `slint.snapshot` | — | accessible-tree dump (id, role, label, text, state) for debugging/stepping |

---

## 5. Execution model

- Headless by default: Slint's software renderer means `slint.launch` works in
  CI without a display server; set `headless: false` to run on a real desktop.
- State round-trips through Suitest's existing **step protocol**: each `code`
  block declares `tool` + `arguments` + optional `assertions` (see the
  `suite.json` in `examples/slint-demo/`), so desktop steps are first-class
  steps, not a separate engine.
- Deterministic replay relies on `accessible-id` stability: an un-tagged widget
  is resolved by label+role, which is stable only if the app's UI copy is.

---

## 6. Testing strategy (how we validate this milestone)

1. **Example smoke suite** — `examples/slint-demo/suite.json` (S1 idle, S2
   submit, S3 reset) targeting `FE_DESKTOP` with provider `slint-mcp`. This is
   the canonical replay artifact and can run at zero tier.
2. **Unit tests** (in `packages/mcp/tests`) — assert:
   - `routing.DEFAULT_ROUTING[TargetKind.FE_DESKTOP] == ("computer-use-mcp", None)`,
   - the three desktop providers are registered in `BUILTIN_SPECS` with
     `kind == "desktop"`, `${provider}.launch` tools, and `command_pin`
     residency flags.
3. **Contract compliance (optional harness)** — a local `slint-mcp`
   implementation (not in this repo; the `rdb` repo is the sample target) must
   satisfy the `tools/list` catalog in [§4](#4-slint-mcp-tool-contract) and
   resolve the `examples/slint-demo` selectors.

---

## 7. Out of scope / follow-ups

- **M14-2** Electron DOM automation detail (Playwright `_electron` selection in
  the `electron-mcp` config).
- OS-native window find/handles beyond computer-use; native accessibility
  (macOS AX / Windows UIA) for non-Slint apps is a later milestone.
- Screenshot diffing / visual regression for desktop is parked (see
  [ROADMAP.md](./ROADMAP.md) backlog).
