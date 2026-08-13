"use strict";

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { detectFramework } = require("../lib/detect-framework.js");

function projectWith(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "suitest-fw-"));
  for (const [rel, content] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, rel), content);
  }
  return dir;
}

test("next.js -> frontend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { next: "^15" } }),
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "nextjs",
    mode: "frontend",
    baseUrl: "http://localhost:3000",
  });
});

test("vite -> frontend :5173", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ devDependencies: { vite: "^6" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:5173");
});

test("nuxt -> frontend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { nuxt: "^3" } }),
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "nuxt",
    mode: "frontend",
    baseUrl: "http://localhost:3000",
  });
});

test("sveltekit -> frontend :5173", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ devDependencies: { "@sveltejs/kit": "^2" } }),
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "sveltekit",
    mode: "frontend",
    baseUrl: "http://localhost:5173",
  });
});

test("vue cli -> frontend :8080", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ devDependencies: { "@vue/cli-service": "^5" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:8080");
});

test("nuxt beats vite when both present", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { nuxt: "^3", vite: "^6" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "nuxt");
});

test("express -> backend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { express: "^4" } }),
  });
  assert.strictEqual(detectFramework(dir).mode, "backend");
});

test("django (manage.py) -> backend :8000", () => {
  const dir = projectWith({ "manage.py": "" });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "django",
    mode: "backend",
    baseUrl: "http://localhost:8000",
  });
});

test("unknown -> null (init akan tanya manual)", () => {
  assert.strictEqual(detectFramework(projectWith({})), null);
});

// --- FE additions ---

test("angular -> frontend :4200", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "@angular/core": "^18" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:4200");
});

test("remix -> frontend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "@remix-run/react": "^2" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "remix");
});

test("astro -> frontend :4321", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { astro: "^4" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:4321");
});

test("astro beats vite when both present", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { astro: "^4", vite: "^6" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "astro");
});

test("gatsby -> frontend :8000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { gatsby: "^5" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:8000");
});

test("qwik -> frontend :5173", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ devDependencies: { "@builder.io/qwik": "^1" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "qwik");
});

test("cra (react-scripts) -> frontend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "react-scripts": "^5" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "cra");
});

test("solid -> frontend :5173", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "solid-js": "^1" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "solid");
});

// --- BE: Node ---

test("nestjs -> backend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "@nestjs/core": "^10" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "nestjs");
});

test("nestjs beats express when both present", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({
      dependencies: { "@nestjs/core": "^10", "@nestjs/platform-express": "^10", express: "^4" },
    }),
  });
  assert.strictEqual(detectFramework(dir).framework, "nestjs");
});

test("fastify -> backend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { fastify: "^5" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "fastify");
});

test("koa -> backend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { koa: "^2" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "koa");
});

test("hapi -> backend :3000", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "@hapi/hapi": "^21" } }),
  });
  assert.strictEqual(detectFramework(dir).framework, "hapi");
});

test("adonisjs -> backend :3333", () => {
  const dir = projectWith({
    "package.json": JSON.stringify({ dependencies: { "@adonisjs/core": "^6" } }),
  });
  assert.strictEqual(detectFramework(dir).baseUrl, "http://localhost:3333");
});

// --- BE: Python ---

test("fastapi (requirements.txt) -> backend :8000", () => {
  const dir = projectWith({ "requirements.txt": "fastapi==0.111.0\nuvicorn[standard]\n" });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "fastapi",
    mode: "backend",
    baseUrl: "http://localhost:8000",
  });
});

test("fastapi (pyproject.toml) -> backend :8000", () => {
  const dir = projectWith({
    "pyproject.toml": '[project]\ndependencies = [\n  "fastapi>=0.111",\n  "uvicorn",\n]\n',
  });
  assert.strictEqual(detectFramework(dir).framework, "fastapi");
});

test("flask (requirements.txt) -> backend :5000", () => {
  const dir = projectWith({ "requirements.txt": "Flask==3.0.0\n" });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "flask",
    mode: "backend",
    baseUrl: "http://localhost:5000",
  });
});

test("django still beats flask/fastapi when manage.py present", () => {
  const dir = projectWith({
    "manage.py": "",
    "requirements.txt": "django\nflask\nfastapi\n",
  });
  assert.strictEqual(detectFramework(dir).framework, "django");
});

test("requirements.txt with no known framework -> falls through to null", () => {
  const dir = projectWith({ "requirements.txt": "requests==2.31.0\n" });
  assert.strictEqual(detectFramework(dir), null);
});

// --- BE: Ruby ---

test("rails (Gemfile) -> backend :3000", () => {
  const dir = projectWith({ Gemfile: 'source "https://rubygems.org"\ngem "rails", "~> 7.1"\n' });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "rails",
    mode: "backend",
    baseUrl: "http://localhost:3000",
  });
});

// --- BE: PHP ---

test("laravel (composer.json) -> backend :8000", () => {
  const dir = projectWith({
    "composer.json": JSON.stringify({ require: { "laravel/framework": "^11.0" } }),
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "laravel",
    mode: "backend",
    baseUrl: "http://localhost:8000",
  });
});

test("malformed composer.json -> null, does not throw", () => {
  const dir = projectWith({ "composer.json": "{not json" });
  assert.strictEqual(detectFramework(dir), null);
});

// --- BE: Go ---

test("gin (go.mod) -> backend :8080", () => {
  const dir = projectWith({
    "go.mod": 'module example.com/app\n\ngo 1.22\n\nrequire github.com/gin-gonic/gin v1.9.1\n',
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "gin",
    mode: "backend",
    baseUrl: "http://localhost:8080",
  });
});

test("echo (go.mod) -> backend :8080", () => {
  const dir = projectWith({
    "go.mod": "module example.com/app\n\nrequire github.com/labstack/echo/v4 v4.12.0\n",
  });
  assert.strictEqual(detectFramework(dir).framework, "echo");
});

test("fiber (go.mod) -> backend :3000", () => {
  const dir = projectWith({
    "go.mod": "module example.com/app\n\nrequire github.com/gofiber/fiber/v2 v2.52.0\n",
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "fiber",
    mode: "backend",
    baseUrl: "http://localhost:3000",
  });
});

// --- BE: Rust ---

test("actix-web (Cargo.toml) -> backend :8080", () => {
  const dir = projectWith({
    "Cargo.toml": '[package]\nname = "app"\nversion = "0.1.0"\n\n[dependencies]\nactix-web = "4"\n',
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "actix-web",
    mode: "backend",
    baseUrl: "http://localhost:8080",
  });
});

test("axum (Cargo.toml) -> backend :3000", () => {
  const dir = projectWith({
    "Cargo.toml": '[package]\nname = "app"\n\n[dependencies]\naxum = "0.7"\ntokio = { version = "1", features = ["full"] }\n',
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "axum",
    mode: "backend",
    baseUrl: "http://localhost:3000",
  });
});

test("rocket (Cargo.toml) -> backend :8000", () => {
  const dir = projectWith({
    "Cargo.toml": '[package]\nname = "app"\n\n[dependencies]\nrocket = "0.5"\n',
  });
  assert.deepStrictEqual(detectFramework(dir), {
    framework: "rocket",
    mode: "backend",
    baseUrl: "http://localhost:8000",
  });
});
