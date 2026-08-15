#!/usr/bin/env node
/**
 * Interpreter resolution under a *short* PATH — the environment an MCP client
 * spawns us with, not a login shell.
 *
 * Both cases here are real failures seen in the field on macOS: `/usr/bin/python3`
 * is 3.9 and shadows a current interpreter, and `uv` lives in `~/.local/bin`
 * which that PATH does not contain. Fake interpreters keep the test hermetic —
 * no real Python or uv is involved.
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

// A stand-in interpreter that answers the `-c "import sys; print(...)"` probe
// with `version`, and nothing else.
function fakePython(dir, name, version) {
  const p = path.join(dir, name);
  fs.writeFileSync(p, `#!/bin/sh\necho "${version}"\n`, { mode: 0o755 });
  return p;
}

function fakeUv(dir, name, pythonPath) {
  const p = path.join(dir, name);
  fs.writeFileSync(
    p,
    [
      "#!/bin/sh",
      'if [ "$1" = "--version" ]; then echo "uv 0.0.0-test"; exit 0; fi',
      `if [ "$1" = "python" ] && [ "$2" = "find" ]; then echo "${pythonPath}"; exit 0; fi`,
      "exit 0",
    ].join("\n"),
    { mode: 0o755 },
  );
  return p;
}

// python.js reads process.env/os.homedir() at call time, so each case sets the
// environment, requires a fresh copy of the module, and restores afterwards.
function withEnv({ pathDirs, home }, fn) {
  const origPath = process.env.PATH;
  const origPin = process.env.SUITEST_PYTHON;
  const origHome = os.homedir;
  process.env.PATH = pathDirs.join(path.delimiter);
  delete process.env.SUITEST_PYTHON;
  if (home) os.homedir = () => home;
  try {
    delete require.cache[require.resolve("../lib/python.js")];
    return fn(require("../lib/python.js"));
  } finally {
    process.env.PATH = origPath;
    if (origPin === undefined) delete process.env.SUITEST_PYTHON;
    else process.env.SUITEST_PYTHON = origPin;
    os.homedir = origHome;
  }
}

function tmpdir(name) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `suitest-${name}-`));
}

test("a too-old python3 does not end the search when a versioned one is next to it", () => {
  const dir = tmpdir("pyver");
  fakePython(dir, "python3", "3.9"); // what /usr/bin/python3 is on macOS
  fakePython(dir, "python3.13", "3.13");

  const found = withEnv({ pathDirs: [dir] }, (py) => py.findPython());

  assert.ok(found, "expected an interpreter to be found");
  assert.strictEqual(found.version, "3.13");
  assert.ok(
    found.cmd.endsWith("python3.13"),
    `expected the versioned interpreter, got ${found.cmd}`,
  );
});

test("uv is found in its own install dir when it is not on PATH", () => {
  const dir = tmpdir("uvhome");
  const home = tmpdir("uvhome-home");
  const localBin = path.join(home, ".local", "bin");
  fs.mkdirSync(localBin, { recursive: true });

  fakePython(dir, "python3", "3.9"); // only an unusable interpreter on PATH
  const managed = fakePython(dir, "managed-python", "3.12");
  fakeUv(localBin, "uv", managed); // uv itself is NOT on PATH

  const found = withEnv({ pathDirs: [dir], home }, (py) => py.findPython());

  assert.ok(found, "expected uv to provide an interpreter");
  assert.strictEqual(found.version, "3.12");
  assert.strictEqual(found.viaUv, true);
});

test("nothing usable anywhere still reports failure", () => {
  const dir = tmpdir("pynone");
  const home = tmpdir("pynone-home");
  fakePython(dir, "python3", "3.9");

  const found = withEnv({ pathDirs: [dir], home }, (py) => py.findPython());

  assert.strictEqual(found, null);
});
