"use strict";

const { test } = require("node:test");
const assert = require("node:assert");
const { PassThrough } = require("node:stream");

const { select, confirm, multiselect } = require("../lib/picker.js");

const KEY_UP = "\x1b[A";
const KEY_DOWN = "\x1b[B";
const KEY_SPACE = " ";
const KEY_ENTER = "\r";
const KEY_CTRL_C = "\x03";
const KEY_ESC = "\x1b";

function pair() {
  const input = new PassThrough();
  const output = new PassThrough();
  output.on("data", () => {}); // drain, we don't assert on rendered frames
  return { input, output };
}

// Same as pair(), but keeps every write so tests can assert on rendered text.
function capturedPair() {
  const input = new PassThrough();
  const output = new PassThrough();
  let written = "";
  output.on("data", (chunk) => {
    written += chunk.toString();
  });
  return { input, output, text: () => written };
}

test("confirm() resolves the default value on bare Enter", async () => {
  const { input, output } = pair();
  const p = confirm("Continue?", { default: "yes" }, { input, output });
  setImmediate(() => input.write(KEY_ENTER));
  assert.strictEqual(await p, true);
});

test("confirm() toggles with arrow keys before resolving", async () => {
  const { input, output } = pair();
  const p = confirm("Continue?", { default: "yes" }, { input, output });
  setImmediate(() => {
    input.write(KEY_UP); // yes -> no (only two rows, any arrow toggles)
    input.write(KEY_ENTER);
  });
  assert.strictEqual(await p, false);
});

test("confirm() rejects with code CANCEL on Ctrl-C", async () => {
  const { input, output } = pair();
  const p = confirm("Continue?", {}, { input, output });
  setImmediate(() => input.write(KEY_CTRL_C));
  await assert.rejects(p, (err) => err.code === "CANCEL");
});

test("confirm() rejects with code BACK on Esc", async () => {
  const { input, output } = pair();
  const p = confirm("Continue?", {}, { input, output });
  setImmediate(() => input.write(KEY_ESC));
  await assert.rejects(p, (err) => err.code === "BACK");
});

test("select() resolves the highlighted item on Enter", async () => {
  const { input, output } = pair();
  const items = [
    { value: "a", label: "Alpha" },
    { value: "b", label: "Beta" },
  ];
  const p = select("Pick one", items, { input, output });
  setImmediate(() => input.write(KEY_ENTER));
  assert.strictEqual(await p, "a");
});

test("select() rejects with code BACK on Esc, CANCEL on Ctrl-C", async () => {
  const items = [{ value: "a", label: "Alpha" }];

  const p1 = pair();
  const back = select("Pick one", items, p1);
  setImmediate(() => p1.input.write(KEY_ESC));
  await assert.rejects(back, (err) => err.code === "BACK");

  const p2 = pair();
  const cancel = select("Pick one", items, p2);
  setImmediate(() => p2.input.write(KEY_CTRL_C));
  await assert.rejects(cancel, (err) => err.code === "CANCEL");
});

test("confirm()'s question and answered lines start with the marker, not the gutter pipe", async () => {
  const { input, output, text } = capturedPair();
  const p = confirm("Continue?", { default: "yes" }, { input, output });
  setImmediate(() => input.write(KEY_ENTER));
  await p;
  const out = text();
  assert.ok(out.includes("◆ Continue?"), `expected the question marker, got: ${JSON.stringify(out)}`);
  assert.ok(out.includes("◇ Continue?"), `expected the collapsed marker, got: ${JSON.stringify(out)}`);
  // The gutter pipe is immediately followed by a space then content (see
  // gutter()) — "│ ◆"/"│ ◇" is exactly the column-2 bug this guards against.
  assert.ok(!out.includes("│ ◆"), `marker should not sit right after a gutter pipe: ${JSON.stringify(out)}`);
  assert.ok(!out.includes("│ ◇"), `marker should not sit right after a gutter pipe: ${JSON.stringify(out)}`);
});

test("multiselect() resolves an empty array on bare Enter (nothing toggled)", async () => {
  const { input, output } = pair();
  const items = [
    { value: "a", label: "Alpha" },
    { value: "b", label: "Beta" },
  ];
  const p = multiselect("Pick some", items, { input, output });
  setImmediate(() => input.write(KEY_ENTER));
  assert.deepStrictEqual(await p, []);
});

test("multiselect() toggles multiple rows with space before confirming", async () => {
  const { input, output } = pair();
  const items = [
    { value: "a", label: "Alpha" },
    { value: "b", label: "Beta" },
    { value: "c", label: "Gamma" },
  ];
  const p = multiselect("Pick some", items, { input, output });
  setImmediate(() => {
    input.write(KEY_SPACE); // check Alpha
    input.write(KEY_DOWN);
    input.write(KEY_DOWN); // move to Gamma, skipping Beta
    input.write(KEY_SPACE); // check Gamma
    input.write(KEY_ENTER);
  });
  assert.deepStrictEqual(await p, ["a", "c"]);
});

test("multiselect() un-toggles on a second space", async () => {
  const { input, output } = pair();
  const items = [{ value: "a", label: "Alpha" }];
  const p = multiselect("Pick some", items, { input, output });
  setImmediate(() => {
    input.write(KEY_SPACE);
    input.write(KEY_SPACE);
    input.write(KEY_ENTER);
  });
  assert.deepStrictEqual(await p, []);
});

test("multiselect() rejects with code BACK on Esc, CANCEL on Ctrl-C", async () => {
  const items = [{ value: "a", label: "Alpha" }];

  const p1 = pair();
  const back = multiselect("Pick some", items, p1);
  setImmediate(() => p1.input.write(KEY_ESC));
  await assert.rejects(back, (err) => err.code === "BACK");

  const p2 = pair();
  const cancel = multiselect("Pick some", items, p2);
  setImmediate(() => p2.input.write(KEY_CTRL_C));
  await assert.rejects(cancel, (err) => err.code === "CANCEL");
});
