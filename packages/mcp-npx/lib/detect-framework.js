"use strict";

/**
 * App-framework detection for `init` — a data table, one entry per framework.
 * The result seeds `suitest.config.json` (mode + baseUrl). Adding a framework =
 * one row here (Node/package.json-based) or one line in the matching
 * ecosystem function below (non-Node manifests).
 */

const fs = require("node:fs");
const path = require("node:path");

// Reads `filename` under cwd, or null if missing/unreadable. Used for
// non-JSON manifests (requirements.txt, pyproject.toml, Gemfile, go.mod,
// Cargo.toml) where we only need a dependency-name substring match, not full
// parsing — no TOML/YAML parser dependency is pulled in for this.
function readTextIfExists(cwd, filename) {
  const p = path.join(cwd, filename);
  if (!fs.existsSync(p)) return null;
  try {
    return fs.readFileSync(p, "utf8");
  } catch {
    return null;
  }
}

// Same idea for JSON manifests (composer.json). package.json keeps its own
// inline parse below since it also needs the merged deps object shape.
function readJsonIfExists(cwd, filename) {
  const text = readTextIfExists(cwd, filename);
  if (text === null) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// Order = priority. Meta-frameworks/full-stack frameworks that ship another
// tool in this list as a dep are listed before that dep so their own
// dev-server port wins: astro/qwik/remix/solid before `vite` (they can ship
// vite as a dependency), nuxt/sveltekit before `vite` (same reason), `next`
// before `express`, `nestjs` before `express`/`fastify` (Nest apps commonly
// list the underlying HTTP adapter as a peer dep).
const FRAMEWORKS = [
  { id: "nextjs", dep: "next", mode: "frontend", baseUrl: "http://localhost:3000" },
  { id: "remix", dep: "@remix-run/react", mode: "frontend", baseUrl: "http://localhost:3000" },
  { id: "astro", dep: "astro", mode: "frontend", baseUrl: "http://localhost:4321" },
  { id: "qwik", dep: "@builder.io/qwik", mode: "frontend", baseUrl: "http://localhost:5173" },
  { id: "nuxt", dep: "nuxt", mode: "frontend", baseUrl: "http://localhost:3000" },
  { id: "sveltekit", dep: "@sveltejs/kit", mode: "frontend", baseUrl: "http://localhost:5173" },
  { id: "gatsby", dep: "gatsby", mode: "frontend", baseUrl: "http://localhost:8000" },
  { id: "cra", dep: "react-scripts", mode: "frontend", baseUrl: "http://localhost:3000" },
  { id: "solid", dep: "solid-js", mode: "frontend", baseUrl: "http://localhost:5173" },
  { id: "vite", dep: "vite", mode: "frontend", baseUrl: "http://localhost:5173" },
  { id: "vue", dep: "@vue/cli-service", mode: "frontend", baseUrl: "http://localhost:8080" },
  { id: "angular", dep: "@angular/core", mode: "frontend", baseUrl: "http://localhost:4200" },
  { id: "nestjs", dep: "@nestjs/core", mode: "backend", baseUrl: "http://localhost:3000" },
  { id: "fastify", dep: "fastify", mode: "backend", baseUrl: "http://localhost:3000" },
  { id: "koa", dep: "koa", mode: "backend", baseUrl: "http://localhost:3000" },
  { id: "hapi", dep: "@hapi/hapi", mode: "backend", baseUrl: "http://localhost:3000" },
  { id: "adonisjs", dep: "@adonisjs/core", mode: "backend", baseUrl: "http://localhost:3333" },
  { id: "express", dep: "express", mode: "backend", baseUrl: "http://localhost:3000" },
];

// Python: manage.py is the unambiguous Django tell (no package.json for
// Python projects). Otherwise scan requirements.txt / pyproject.toml for a
// dependency-name substring — good enough since we only need the name, not
// full TOML semantics. FastAPI checked before Flask: arbitrary tie-break,
// no known case where a project depends on both meaningfully.
function detectPython(cwd) {
  if (fs.existsSync(path.join(cwd, "manage.py"))) {
    return { framework: "django", mode: "backend", baseUrl: "http://localhost:8000" };
  }
  const req = readTextIfExists(cwd, "requirements.txt");
  const pyproject = readTextIfExists(cwd, "pyproject.toml");
  if (req === null && pyproject === null) return null;
  const text = `${req || ""}\n${pyproject || ""}`;
  if (/\bfastapi\b/i.test(text)) {
    return { framework: "fastapi", mode: "backend", baseUrl: "http://localhost:8000" };
  }
  if (/\bflask\b/i.test(text)) {
    return { framework: "flask", mode: "backend", baseUrl: "http://localhost:5000" };
  }
  return null;
}

// Ruby: Gemfile, looking for the `rails` gem declaration.
function detectRuby(cwd) {
  const gemfile = readTextIfExists(cwd, "Gemfile");
  if (gemfile && /gem\s+["']rails["']/i.test(gemfile)) {
    return { framework: "rails", mode: "backend", baseUrl: "http://localhost:3000" };
  }
  return null;
}

// Go: go.mod `require` lines. First match wins; order is an arbitrary
// tie-break since a project depending on more than one of these is rare.
function detectGo(cwd) {
  const goMod = readTextIfExists(cwd, "go.mod");
  if (!goMod) return null;
  if (/github\.com\/gin-gonic\/gin/.test(goMod)) {
    return { framework: "gin", mode: "backend", baseUrl: "http://localhost:8080" };
  }
  if (/github\.com\/labstack\/echo/.test(goMod)) {
    return { framework: "echo", mode: "backend", baseUrl: "http://localhost:8080" };
  }
  if (/github\.com\/gofiber\/fiber/.test(goMod)) {
    return { framework: "fiber", mode: "backend", baseUrl: "http://localhost:3000" };
  }
  return null;
}

// Rust: Cargo.toml dependency-name substring, same reasoning as Python.
function detectRust(cwd) {
  const cargoToml = readTextIfExists(cwd, "Cargo.toml");
  if (!cargoToml) return null;
  if (/\bactix-web\b/i.test(cargoToml)) {
    return { framework: "actix-web", mode: "backend", baseUrl: "http://localhost:8080" };
  }
  if (/\baxum\b/i.test(cargoToml)) {
    return { framework: "axum", mode: "backend", baseUrl: "http://localhost:3000" };
  }
  if (/\brocket\b/i.test(cargoToml)) {
    return { framework: "rocket", mode: "backend", baseUrl: "http://localhost:8000" };
  }
  return null;
}

// PHP: composer.json is valid JSON, so this reuses the same dep-map pattern
// as package.json rather than a text-substring reader.
function detectPhp(cwd) {
  const composer = readJsonIfExists(cwd, "composer.json");
  if (!composer) return null;
  const deps = { ...(composer.require || {}) };
  if (deps["laravel/framework"]) {
    return { framework: "laravel", mode: "backend", baseUrl: "http://localhost:8000" };
  }
  return null;
}

function detectFramework(cwd) {
  const python = detectPython(cwd);
  if (python) return python;

  const ruby = detectRuby(cwd);
  if (ruby) return ruby;

  const go = detectGo(cwd);
  if (go) return go;

  const rust = detectRust(cwd);
  if (rust) return rust;

  const pkgPath = path.join(cwd, "package.json");
  if (fs.existsSync(pkgPath)) {
    let pkg;
    try {
      pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
    } catch {
      pkg = null;
    }
    if (pkg) {
      const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
      for (const fw of FRAMEWORKS) {
        if (deps[fw.dep]) {
          return { framework: fw.id, mode: fw.mode, baseUrl: fw.baseUrl };
        }
      }
    }
  }

  const php = detectPhp(cwd);
  if (php) return php;

  return null;
}

module.exports = { detectFramework, FRAMEWORKS };
