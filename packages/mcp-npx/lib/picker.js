"use strict";

/**
 * Minimal arrow-key + type-to-filter picker, stdlib only (readline raw mode).
 * Stands in for inquire::Select from the jira reference — no dependency.
 */

const readline = require("node:readline");
const theme = require("./theme.js");

/**
 * @param {string} prompt
 * @param {{value:string,label:string,hint?:string}[]} items
 * @param {{input?:NodeJS.ReadableStream, output?:NodeJS.WritableStream}} [streams]
 * @returns {Promise<string>} chosen value (rejects on cancel / no TTY)
 */
function select(prompt, items, streams = {}) {
  const stdin = streams.input || process.stdin;
  const stdout = streams.output || process.stdout;

  if (!stdin.isTTY && !streams.input) {
    return Promise.reject(
      new Error("no TTY for interactive picker — pass --client <target>"),
    );
  }

  return new Promise((resolve, reject) => {
    let filter = "";
    let index = 0;

    // Align the second column so hints line up like the jira picker.
    const labelWidth = Math.max(...items.map((i) => i.label.length)) + 2;

    const visible = () =>
      filter
        ? items.filter((i) =>
            i.label.toLowerCase().includes(filter.toLowerCase()),
          )
        : items;

    let lastLines = 0;

    function render() {
      const rows = visible();
      if (index >= rows.length) index = Math.max(0, rows.length - 1);

      const lines = [];
      lines.push(theme.point(`${prompt}${filter ? `  (filter: ${filter})` : ""}`, { marker: "◆" }, stdout));
      for (let i = 0; i < rows.length; i++) {
        const it = rows[i];
        const marker = i === index ? ">" : " ";
        const label = it.label.padEnd(labelWidth);
        const hint = it.hint ? `(${it.hint})` : "";
        lines.push(theme.gutter(`${marker} ${label}${hint}`, {}, stdout));
      }
      lines.push(theme.gutter("[↑↓ move, enter select, esc back, type to filter]", {}, stdout));

      // Redraw in place: move cursor up over the previous block and clear.
      // No trailing newline after the block — the cursor stays on its last
      // row (end of the gutter line) instead of idling on a blank row below
      // with no "│", which reads as detached from the connector column.
      if (lastLines > 0) {
        readline.moveCursor(stdout, 0, -(lastLines - 1));
      }
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(lines.join("\n"));
      lastLines = lines.length;
    }

    // Replace the expanded question block with a single answered line —
    // once a step is past, it collapses into its own "◇ label  value" point
    // instead of leaving the full option list on screen.
    function collapse(line) {
      readline.moveCursor(stdout, 0, -(lastLines - 1));
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(line + "\n");
    }

    function cleanup() {
      stdin.removeListener("keypress", onKeypress);
      if (stdin.isTTY) stdin.setRawMode(false);
      stdin.pause();
    }

    function onKeypress(str, key) {
      if (!key) return;
      const rows = visible();

      if (key.ctrl && key.name === "c") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("selection cancelled"), { code: "CANCEL" }));
      }
      if (key.name === "escape") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("back"), { code: "BACK" }));
      }
      if (key.name === "up") {
        index = index > 0 ? index - 1 : Math.max(0, rows.length - 1);
        return render();
      }
      if (key.name === "down") {
        index = rows.length ? (index + 1) % rows.length : 0;
        return render();
      }
      if (key.name === "return") {
        if (!rows.length) return; // nothing matches the filter
        const chosen = rows[index];
        cleanup();
        collapse(theme.point(`${prompt}  ${theme.accent(chosen.label, stdout)}`, {}, stdout));
        return resolve(chosen.value);
      }
      if (key.name === "backspace") {
        filter = filter.slice(0, -1);
        index = 0;
        return render();
      }
      // printable char -> extend filter
      if (str && str.length === 1 && !key.ctrl && !key.meta) {
        filter += str;
        index = 0;
        return render();
      }
    }

    readline.emitKeypressEvents(stdin);
    if (stdin.isTTY) stdin.setRawMode(true);
    stdin.resume();
    stdin.on("keypress", onKeypress);
    render();
  });
}

/**
 * Yes/No radio prompt — same keypress/redraw plumbing as select(), but a
 * fixed two-row ○/● list instead of a filterable one.
 * @param {string} prompt
 * @param {{default?: "yes"|"no"}} [opts]
 * @param {{input?:NodeJS.ReadableStream, output?:NodeJS.WritableStream}} [streams]
 * @returns {Promise<boolean>} rejects on cancel / no TTY
 */
function confirm(prompt, opts = {}, streams = {}) {
  const stdin = streams.input || process.stdin;
  const stdout = streams.output || process.stdout;
  const rows = [
    { value: true, label: "Yes" },
    { value: false, label: "No" },
  ];

  if (!stdin.isTTY && !streams.input) {
    return Promise.reject(new Error("no TTY for interactive prompt"));
  }

  return new Promise((resolve, reject) => {
    let index = opts.default === "yes" ? 0 : 1;
    let lastLines = 0;

    function render() {
      const lines = [theme.point(prompt, { marker: "◆" }, stdout)];
      for (let i = 0; i < rows.length; i++) {
        const selected = i === index;
        const marker = selected ? "●" : "○";
        const label = selected ? theme.accent(rows[i].label, stdout) : rows[i].label;
        lines.push(theme.gutter(`  ${marker} ${label}`, {}, stdout));
      }
      lines.push(theme.gutter("[↑↓ toggle, enter confirm, esc back]", {}, stdout));
      // See select()'s render() for why there's no trailing newline here.
      if (lastLines > 0) readline.moveCursor(stdout, 0, -(lastLines - 1));
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(lines.join("\n"));
      lastLines = lines.length;
    }

    // Replace the expanded Yes/No block with a single answered line — see
    // select()'s collapse() for why.
    function collapse(line) {
      readline.moveCursor(stdout, 0, -(lastLines - 1));
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(line + "\n");
    }

    function cleanup() {
      stdin.removeListener("keypress", onKeypress);
      if (stdin.isTTY) stdin.setRawMode(false);
      stdin.pause();
    }

    function onKeypress(str, key) {
      if (!key) return;
      if (key.ctrl && key.name === "c") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("selection cancelled"), { code: "CANCEL" }));
      }
      if (key.name === "escape") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("back"), { code: "BACK" }));
      }
      if (["up", "down", "left", "right"].includes(key.name)) {
        index = index === 0 ? 1 : 0;
        return render();
      }
      if (key.name === "return") {
        cleanup();
        collapse(theme.point(`${prompt}  ${theme.accent(rows[index].label, stdout)}`, {}, stdout));
        return resolve(rows[index].value);
      }
    }

    readline.emitKeypressEvents(stdin);
    if (stdin.isTTY) stdin.setRawMode(true);
    stdin.resume();
    stdin.on("keypress", onKeypress);
    render();
  });
}

/**
 * Checkbox multi-select — same keypress/redraw plumbing as select(), but
 * space toggles membership in a set instead of enter picking one row.
 * @param {string} prompt
 * @param {{value:string,label:string,hint?:string}[]} items
 * @param {{input?:NodeJS.ReadableStream, output?:NodeJS.WritableStream}} [streams]
 * @returns {Promise<string[]>} chosen values, in item order (rejects on cancel / no TTY)
 */
function multiselect(prompt, items, streams = {}) {
  const stdin = streams.input || process.stdin;
  const stdout = streams.output || process.stdout;

  if (!stdin.isTTY && !streams.input) {
    return Promise.reject(
      new Error("no TTY for interactive picker — pass --client <target>"),
    );
  }

  return new Promise((resolve, reject) => {
    let index = 0;
    const checked = new Set();
    const labelWidth = Math.max(...items.map((i) => i.label.length)) + 2;
    let lastLines = 0;

    function render() {
      const lines = [theme.point(prompt, { marker: "◆" }, stdout)];
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        const isChecked = checked.has(it.value);
        const box = isChecked ? "◉" : "○";
        const boxed = i === index ? theme.accent(box, stdout) : box;
        const label = it.label.padEnd(labelWidth);
        const hint = it.hint ? `(${it.hint})` : "";
        lines.push(theme.gutter(`${boxed} ${label}${hint}`, {}, stdout));
      }
      lines.push(theme.gutter("[space toggle, ↑↓ move, enter confirm, esc back]", {}, stdout));
      if (lastLines > 0) readline.moveCursor(stdout, 0, -(lastLines - 1));
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(lines.join("\n"));
      lastLines = lines.length;
    }

    function collapse(line) {
      readline.moveCursor(stdout, 0, -(lastLines - 1));
      readline.cursorTo(stdout, 0);
      readline.clearScreenDown(stdout);
      stdout.write(line + "\n");
    }

    function cleanup() {
      stdin.removeListener("keypress", onKeypress);
      if (stdin.isTTY) stdin.setRawMode(false);
      stdin.pause();
    }

    function onKeypress(str, key) {
      if (!key) return;
      if (key.ctrl && key.name === "c") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("selection cancelled"), { code: "CANCEL" }));
      }
      if (key.name === "escape") {
        cleanup();
        stdout.write("\n");
        return reject(Object.assign(new Error("back"), { code: "BACK" }));
      }
      if (key.name === "up") {
        index = index > 0 ? index - 1 : items.length - 1;
        return render();
      }
      if (key.name === "down") {
        index = (index + 1) % items.length;
        return render();
      }
      if (key.name === "space") {
        const value = items[index].value;
        if (checked.has(value)) checked.delete(value);
        else checked.add(value);
        return render();
      }
      if (key.name === "return") {
        cleanup();
        const chosen = items.filter((it) => checked.has(it.value));
        const summary = chosen.length
          ? chosen.map((it) => theme.accent(it.label, stdout)).join(", ")
          : theme.fg3("(none)", stdout);
        collapse(theme.point(`${prompt}  ${summary}`, {}, stdout));
        return resolve(chosen.map((it) => it.value));
      }
    }

    readline.emitKeypressEvents(stdin);
    if (stdin.isTTY) stdin.setRawMode(true);
    stdin.resume();
    stdin.on("keypress", onKeypress);
    render();
  });
}

module.exports = { select, confirm, multiselect };
