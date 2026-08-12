"use strict";

// Small, dependency-free terminal styling used by the published Suitest CLI.
// Keep output readable when stdout is redirected or the terminal has no color.
const tty = require("node:tty");

const enabled = Boolean(process.env.FORCE_COLOR) || tty.isatty(1);
const wrap = (code) => (value) => (enabled ? `[${code}m${value}[0m` : String(value));

const violet = wrap(35);
const accent = wrap(36);
const muted = wrap(90);
const bold = wrap(1);

function point(label, { color = accent } = {}) {
  return `${muted("›")} ${color(label)}`;
}

function step(title, lines = [], { color = accent } = {}) {
  const body = Array.isArray(lines) ? lines : [lines];
  return [bold(color(`◆ ${title}`)), ...body.map((line) => `  ${line}`)].join("\n");
}

function panel(lines, { title = "", color = accent } = {}) {
  const body = Array.isArray(lines) ? lines : [lines];
  const width = Math.max(title.length, ...body.map((line) => String(line).length), 0);
  const top = `╭─${title ? ` ${color(title)} ` : ""}${"─".repeat(Math.max(0, width - title.length + 1))}╮`;
  const rows = body.map((line) => `│ ${String(line).padEnd(width)} │`);
  return [top, ...rows, `╰${"─".repeat(width + 2)}╯`].join("\n");
}

function banner() {
  return `${bold(violet("Suitest"))} ${muted("local QA workspace")}`;
}

module.exports = { accent, banner, bold, muted, panel, point, step, violet };
