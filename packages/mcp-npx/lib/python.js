"use strict";

/**
 * Locate a Python >= 3.11 interpreter. Shared by the server launcher (bin)
 * and the installer's prereq check.
 *
 * Resolution order:
 *   1. $SUITEST_PYTHON, then `python3` / `python`, then the versioned names
 *      (`python3.14` … `python3.11`) on PATH.
 *   2. Fallback: a `uv`-managed Python. If the client has no system Python but
 *      has `uv` (a single static binary), we provision one automatically so
 *      "test my app" works without the user installing Python by hand.
 *
 * Both stages have to cope with a *short* PATH. An MCP client (or any GUI-
 * launched process) spawns us with something close to `/usr/bin:/bin`, not the
 * user's shell PATH, which breaks the naive lookups in two ways:
 *   - `/usr/bin/python3` is frequently an old system build (3.9 on macOS) that
 *     shadows a current `python3.13` sitting in the same or a later directory;
 *   - `uv` installs itself to `~/.local/bin`, which is usually absent from that
 *     PATH, so the fallback whose whole job is "no manual Python install
 *     needed" would report uv missing on a machine that has it.
 */

const { spawnSync } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");

const MIN_PY = [3, 11];

// Tried after the bare names, newest first. A bare `python3` that is too old
// must not end the search while a usable interpreter sits next to it.
const VERSIONED = ["python3.14", "python3.13", "python3.12", "python3.11"];

// uv's own installer targets ~/.local/bin; the cargo route lands in ~/.cargo/bin.
function uvCandidates() {
  const home = os.homedir();
  return [
    "uv",
    path.join(home, ".local", "bin", "uv"),
    path.join(home, ".cargo", "bin", "uv"),
  ];
}

function probeVersion(cmd, args = []) {
  const probe = spawnSync(cmd, [
    ...args,
    "-c",
    "import sys; print('%d.%d' % sys.version_info[:2])",
  ]);
  if (probe.status !== 0) return null;
  const [maj, min] = String(probe.stdout).trim().split(".").map(Number);
  if (Number.isNaN(maj) || Number.isNaN(min)) return null;
  if (maj > MIN_PY[0] || (maj === MIN_PY[0] && min >= MIN_PY[1])) {
    return `${maj}.${min}`;
  }
  return null;
}

// First uv that answers `--version`, or null when none is installed.
function findUv() {
  for (const uv of uvCandidates()) {
    if (spawnSync(uv, ["--version"]).status === 0) return uv;
  }
  return null;
}

// Provision/locate a uv-managed interpreter. Returns an absolute python path or
// null when uv is absent or the install fails (offline, etc.).
function findUvPython() {
  const uv = findUv();
  if (!uv) return null;

  const target = `${MIN_PY[0]}.${Math.max(MIN_PY[1], 12)}`; // 3.12
  // Install is idempotent and fast when the interpreter is already present.
  spawnSync(uv, ["python", "install", target], { stdio: "ignore" });

  const found = spawnSync(uv, ["python", "find", target], { encoding: "utf8" });
  if (found.status !== 0) return null;
  const python = String(found.stdout).trim().split("\n")[0].trim();
  if (!python) return null;
  const version = probeVersion(python);
  return version ? { cmd: python, version, viaUv: true } : null;
}

function findPython() {
  const candidates = process.env.SUITEST_PYTHON
    ? [process.env.SUITEST_PYTHON]
    : ["python3", "python", ...VERSIONED];
  for (const cmd of candidates) {
    const version = probeVersion(cmd);
    if (version) return { cmd, version };
  }
  return findUvPython();
}

module.exports = { MIN_PY, VERSIONED, findPython, findUv, findUvPython, probeVersion };
