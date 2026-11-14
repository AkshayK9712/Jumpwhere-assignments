// Small DOM helpers. Everything is built with createElement and text nodes (never raw HTML strings),
// so text that comes from the API can never be interpreted as HTML (XSS-safe).
let uid = 0;
const PROPS = new Set(["value", "checked", "disabled", "selected", "hidden", "required", "multiple"]);

function append(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** h("div", { class: "card", onclick: fn }, "text", h("span", {}, "child")) */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs || {})) {
    if (val === null || val === undefined || val === false) continue;
    if (key === "class") el.className = val;
    else if (key.startsWith("on") && typeof val === "function") el.addEventListener(key.slice(2).toLowerCase(), val);
    else if (PROPS.has(key)) el[key] = val;
    else el.setAttribute(key, val === true ? "" : String(val));
  }
  append(el, children);
  return el;
}

// ---------- feedback ----------
export function loading(message = "Loading…") {
  return h("div", { class: "loading", role: "status" }, h("span", { class: "spinner", "aria-hidden": "true" }), message);
}

export function toast(message, type = "info", ms = 4500) {
  const host = document.getElementById("toasts");
  if (!host) return;
  const el = h("div", { class: `toast toast-${type}`, role: type === "error" ? "alert" : "status" }, message);
  host.append(el);
  setTimeout(() => el.remove(), ms);
}

export function banner(message, type = "error") {
  return h("div", { class: `banner banner-${type}`, role: type === "error" ? "alert" : "status" }, message);
}

export function confirmDialog({ title = "Are you sure?", message = "", confirmText = "Confirm", cancelText = "Cancel", danger = false }) {
  return new Promise((resolve) => {
    const dlg = h("dialog", { class: "dialog", "aria-labelledby": "dlg-title" });
    const finish = (answer) => {
      dlg.close();
      dlg.remove();
      resolve(answer);
    };
    dlg.append(
      h("h2", { id: "dlg-title" }, title),
      h("p", {}, message),
      h("div", { class: "dialog-actions" },
        h("button", { type: "button", class: "btn", onclick: () => finish(false) }, cancelText),
        h("button", { type: "button", class: `btn ${danger ? "btn-danger" : "btn-primary"}`, autofocus: true, onclick: () => finish(true) }, confirmText),
      ),
    );
    dlg.addEventListener("cancel", (e) => {
      e.preventDefault();
      finish(false);
    });
    document.body.append(dlg);
    dlg.showModal();
  });
}

/** Disable a button and show a "busy" label while an async action runs. */
export function setBusy(button, busy, busyText = "Please wait…") {
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = busyText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.label || button.textContent;
    button.disabled = false;
  }
}

// ---------- badges ----------
export const badge = (text, kind = "muted") => h("span", { class: `badge badge-${kind}` }, text);
const STATUS_KIND = { active: "success", inactive: "muted", faulty: "danger" };
const PRIORITY_KIND = { low: "muted", medium: "info", high: "warn", critical: "danger" };
const ROLE_KIND = { admin: "danger", user: "info", guest: "muted" };
export const statusBadge = (s) => badge(s, STATUS_KIND[s] || "muted");
export const priorityBadge = (p) => badge(p, PRIORITY_KIND[p] || "muted");
export const roleBadge = (r) => badge(r, ROLE_KIND[r] || "muted");

// ---------- forms ----------
/** A labelled input with its own error message. Returns { el, input, value, setError }. */
export function field({ label, name, type = "text", value = "", required = false, placeholder = "", hint = "",
  options = null, textarea = false, autocomplete, min, max, step, maxlength, disabled = false }) {
  const id = `f-${name.replace(/\W/g, "-")}-${++uid}`;
  let input;
  if (options) {
    input = h("select", { id, name, disabled },
      options.map((o) => h("option", { value: o.value, selected: o.value === value }, o.label)));
  } else if (textarea) {
    input = h("textarea", { id, name, rows: 4, maxlength, placeholder, disabled });
    input.value = value ?? "";
  } else {
    input = h("input", { id, name, type, placeholder, autocomplete, min, max, step, maxlength, disabled, required });
    input.value = value ?? "";
  }
  const error = h("p", { class: "field-error", id: `${id}-err`, role: "alert" });
  input.setAttribute("aria-describedby", error.id);

  const el = h("div", { class: "field" },
    h("label", { for: id }, label, required ? h("span", { class: "req", "aria-hidden": "true" }, " *") : null),
    input,
    hint ? h("p", { class: "hint" }, hint) : null,
    error,
  );
  return {
    el,
    input,
    get value() {
      return input.value;
    },
    setError(message) {
      error.textContent = message || "";
      el.classList.toggle("has-error", Boolean(message));
      input.setAttribute("aria-invalid", message ? "true" : "false");
    },
  };
}

/** Show { "metadata.thresholds.min": "msg" } next to matching fields; return messages with no field. */
export function applyErrors(fields, errors) {
  Object.values(fields).forEach((f) => f.setError(""));
  const names = Object.keys(fields);
  const unmatched = [];
  for (const [key, message] of Object.entries(errors || {})) {
    const target = names.find((n) => n === key)
      ?? names.find((n) => n.startsWith(`${key}.`))
      ?? names.find((n) => key.startsWith(`${n}.`));
    if (target) fields[target].setError(message);
    else unmatched.push(message);
  }
  const firstBad = Object.values(fields).find((f) => f.el.classList.contains("has-error"));
  firstBad?.input.focus();
  return unmatched;
}

// ---------- pagination ----------
export function pager({ page, pages, total, pageSize, onPage, onPageSize }) {
  return h("div", { class: "pager" },
    h("button", { type: "button", class: "btn btn-sm", disabled: page <= 1, onclick: () => onPage(page - 1) }, "← Prev"),
    h("span", { class: "pager-info" }, total ? `Page ${page} of ${pages} · ${total} total` : "No results"),
    h("button", { type: "button", class: "btn btn-sm", disabled: page >= pages, onclick: () => onPage(page + 1) }, "Next →"),
    h("select", { "aria-label": "Rows per page", onchange: (e) => onPageSize(Number(e.target.value)) },
      [10, 20, 50].map((n) => h("option", { value: n, selected: n === pageSize }, `${n} / page`))),
  );
}
