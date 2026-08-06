"use strict";

/**
 * Suitest CLI branding — ANSI colors, banner, bordered panels. Stdlib only
 * (no chalk/boxen), colors bound to the same tokens as apps/web/tailwind.config.ts
 * (CLAUDE.md §3.3), so the terminal and the dashboard read as one product.
 */

const CODES = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  // approximate 24-bit tokens as 256-color for wide terminal support
  accent: "\x1b[38;5;114m", // #4ade80
  red: "\x1b[38;5;210m", // #f87171
  amber: "\x1b[38;5;221m", // #fbbf24
  violet: "\x1b[38;5;146m", // #a78bfa
  fg1: "\x1b[38;5;255m", // #fafafa
  fg3: "\x1b[38;5;247m", // #a3a3a3
  border: "\x1b[38;5;238m", // #262626-ish (visible on dark bg)
};

function colorEnabled(stream = process.stdout) {
  return Boolean(stream && stream.isTTY) && !process.env.NO_COLOR;
}

function paint(code) {
  return (text, stream = process.stdout) =>
    colorEnabled(stream) ? `${code}${text}${CODES.reset}` : text;
}

const accent = paint(CODES.accent);
const red = paint(CODES.red);
const amber = paint(CODES.amber);
const violet = paint(CODES.violet);
const fg1 = paint(CODES.bold + CODES.fg1);
const fg3 = paint(CODES.fg3);
const border = paint(CODES.border);

// Small boxed wordmark, accent green like the real logomark (apps/web/public/logo.svg).
// Deliberately plain block letters, not figlet — no dependency, and it collapses
// to three lines of plain text when colorEnabled() is false.
function banner(stream = process.stdout) {
  const word = "S U I T E S T";
  const width = word.length + 4;
  const top = `┌${"─".repeat(width)}┐`;
  const mid = `│  ${word}  │`;
  const bot = `└${"─".repeat(width)}┘`;
  return [accent(top, stream), accent(mid, stream), accent(bot, stream)].join("\n");
}

// Prefix a line with the wizard-step connector column. Defaults to accent —
// `border` (#262626-ish) is a box-edge color, meant to sit next to bright
// content; alone on a near-black background it's effectively invisible.
function gutter(text, { color = accent } = {}, stream = process.stdout) {
  return `${color("│", stream)}${text ? ` ${text}` : ""}`;
}

// A row that IS a point on the connector column — the marker sits at column
// 0, same spot gutter() puts "│". Never combine the two on one row (that's
// what pushed markers a cell to the right of the "│" column in v2).
function point(text, { marker = "◇", color = accent } = {}, stream = process.stdout) {
  return color(`${marker} ${text}`, stream);
}

// One step in a connected wizard flow: a labeled rule, then body lines under
// a shared "│" gutter, with blank connector lines above/below so consecutive
// step()/prompt blocks read as one continuous flow (not floating boxes).
function step(label, lines, { marker = "◇", color = accent } = {}, stream = process.stdout) {
  const body = Array.isArray(lines) ? lines : String(lines).split("\n");
  const rule = "─".repeat(Math.max(3, 30 - label.length));
  const out = [point(`${label} ${rule}`, { marker, color }, stream), gutter("", { color }, stream)];
  for (const line of body) out.push(gutter(fg1(line, stream), { color }, stream));
  out.push(gutter("", { color }, stream));
  return out.join("\n");
}

// Bordered panel around a block of lines. `color` picks the border paint
// function (accent/red/amber/violet/border); defaults to the neutral border.
function panel(lines, { title, color = border } = {}, stream = process.stdout) {
  const body = Array.isArray(lines) ? lines : String(lines).split("\n");
  const contentWidth = Math.max(
    title ? title.length : 0,
    ...body.map((l) => l.length),
    20,
  );
  const rule = "─".repeat(contentWidth + 2);
  const out = [];
  if (title) {
    const pad = "─".repeat(Math.max(0, contentWidth + 2 - title.length - 3));
    out.push(color(`┌─ ${title} ${pad}┐`, stream));
  } else {
    out.push(color(`┌${rule}┐`, stream));
  }
  for (const line of body) {
    out.push(`${color("│", stream)} ${fg1(line.padEnd(contentWidth), stream)} ${color("│", stream)}`);
  }
  out.push(color(`└${rule}┘`, stream));
  return out.join("\n");
}

module.exports = {
  colorEnabled,
  accent,
  red,
  amber,
  violet,
  fg1,
  fg3,
  border,
  banner,
  panel,
  gutter,
  point,
  step,
};
