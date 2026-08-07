# slint-demo

Deterministic sample target used to exercise the bundled `slint-mcp` provider
(M14 desktop testing). It is a plain [Slint](https://slint.dev/) screen — no
browser, no operating-system window automation required.

> **Scope note:** this example lives here for *demo/smoke-test* purposes only.
> To actually automate a real Slint app you point the slint-mcp runner at that
> app's own binary via `command_pin`. Nothing in this repository reads from or
> writes to the `rdb` repo.

## How it maps to slint-mcp selectors

`slint-mcp` drives the app through Slint's **accessible tree** (the same
semantics used by screen readers). Selector priority is:

1. `accessible-id` (most explicit, like a `data-testid`)
2. `accessible-label` + `accessible-role`

Every interactive element in `ui/login-screen.slint` is tagged:

| Widget     | `accessible-id`       | `accessible-role` | Purpose                       |
|------------|-----------------------|-------------------|-------------------------------|
| LineEdit   | `input-email`         | text input        | login email                   |
| LineEdit   | `input-password`      | text input        | login password                |
| CheckBox   | `checkbox-remember`   | check box         | "remember me"                 |
| Button     | `btn-submit`          | button            | submit -> status "submitted"  |
| Button     | `btn-reset`           | button            | reset -> status "idle"        |
| Text       | `label-status`        | text              | assertion target              |

## Example slint-mcp steps

The following steps assume a runner that launches `UI/login-screen.slint` and
exposes an in-process render (headless software renderer).

```yaml
- step: Fill the email field
  tool: slint.set_property
  params: { accessible_id: "input-email", value: "qa@example.com" }

- step: Type the password
  tool: slint.type_text
  params: { selector: '[id="input-password"]', text: "s3cret" }

- step: Toggle remember me
  tool: slint.click
  params: { selector: '[id="checkbox-remember"]' }

- step: Submit the form
  tool: slint.click
  params: { selector: '[id="btn-submit"]' }

- step: Assert the status text
  tool: slint.assert_text
  params: { selector: '[id="label-status"]', text: "submitted" }
```

Selectors may also use label/role pairs, e.g. `{ label: "Submit", role: "button" }`
when an element is not tagged with an `accessible-id`.

## Running it

The `.slint` file is self-contained (only `std-widgets`) and renders headlessly
with Slint's software renderer, so it works in CI without a display server.

See `docs/DESKTOP_TESTING.md` for the full slint-mcp protocol contract and how
to point the runner at a real application binary.
