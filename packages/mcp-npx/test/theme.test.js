"use strict";

const { test } = require("node:test");
const assert = require("node:assert");

const theme = require("../lib/theme.js");

test("theme exports the API used by suitest onboard", () => {
  for (const name of ["accent", "banner", "muted", "panel", "point", "step", "violet"]) {
    assert.strictEqual(typeof theme[name], "function", `${name} is missing`);
  }
});

test("theme renders readable output without terminal escape sequences", () => {
  assert.match(theme.banner(), /Suitest/);
  assert.match(theme.step("create account", ["Use this account to log in."]), /create account/);
  assert.match(theme.point("email:"), /email:/);
  assert.match(theme.panel(["dashboard : http://127.0.0.1:4000"], { title: "ready" }), /ready/);
  const rendered = [theme.banner(), theme.step("x"), theme.point("x"), theme.panel(["x"])].join("\n");
  assert.strictEqual(rendered.includes("["), false, "unexpected ANSI escape in non-TTY test output");
});
