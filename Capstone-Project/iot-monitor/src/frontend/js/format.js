// Pure helpers (no DOM) so they can be unit-tested with Node.

/** The API sends UTC; SQLite omits the timezone, so assume UTC when there is none. */
export function parseApiDate(value) {
  if (!value) return null;
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(value);
  const d = new Date(hasZone ? value : `${value}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(value) {
  const d = parseApiDate(value);
  return d ? d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";
}

export function titleCase(text) {
  const s = String(text ?? "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** datetime-local inputs give "2026-11-14T10:30" in local time; the API wants an ISO instant. */
export function localInputToIso(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function debounce(fn, ms = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export function toInt(value, fallback) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

export function describeThresholds(t) {
  if (!t) return "—";
  const { min, max } = t;
  if (min != null && max != null) return `${min} to ${max}`;
  if (min != null) return `at least ${min}`;
  if (max != null) return `at most ${max}`;
  return "—";
}
