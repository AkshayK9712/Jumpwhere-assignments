// Pure helpers for the dashboard (no DOM), unit-tested with Node.
export const POLL_MS = 5000;

export const RANGE_PRESETS = [
  { id: "1h", label: "Last hour", ms: 3600e3 },
  { id: "6h", label: "Last 6 hours", ms: 6 * 3600e3 },
  { id: "24h", label: "Last 24 hours", ms: 24 * 3600e3 },
  { id: "7d", label: "Last 7 days", ms: 7 * 86400e3 },
  { id: "30d", label: "Last 30 days", ms: 30 * 86400e3 },
  { id: "custom", label: "Custom range", ms: null },
];

/**
 * Presets are "live" (they end now, so the dashboard keeps polling).
 * A custom range is fixed. Returns { from, to, live } or { error }.
 */
export function resolveRange(preset, customFrom, customTo, now = new Date()) {
  if (preset === "custom") {
    const from = new Date(customFrom);
    const to = new Date(customTo);
    if (!customFrom || !customTo || Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
      return { error: "Choose both a start and an end time." };
    }
    if (from >= to) return { error: "The start must be before the end." };
    if (to - from > 366 * 86400e3) return { error: "The range cannot be longer than 366 days." };
    return { from, to, live: false };
  }
  const found = RANGE_PRESETS.find((p) => p.id === preset && p.ms) || RANGE_PRESETS[2];
  return { from: new Date(now.getTime() - found.ms), to: now, live: true };
}

/** Keep the number of chart points small: ~360 max for minutes, ~336 for hours. */
export function pickInterval(rangeMs) {
  if (rangeMs <= 6 * 3600e3) return "minute";
  if (rangeMs <= 14 * 86400e3) return "hour";
  return "day";
}

export function seriesStats(points) {
  if (!points || points.length === 0) return null;
  let count = 0;
  let weighted = 0;
  let min = Infinity;
  let max = -Infinity;
  for (const p of points) {
    count += p.count;
    weighted += p.avg * p.count;
    min = Math.min(min, p.min);
    max = Math.max(max, p.max);
  }
  return { count, min, max, avg: count ? weighted / count : 0 };
}

export function seriesToCsv(points, { unit } = {}) {
  const suffix = unit ? ` (${unit})` : "";
  const lines = [`bucket_utc,avg${suffix},min${suffix},max${suffix},readings`];
  for (const p of points) lines.push([new Date(p.bucket).toISOString(), p.avg, p.min, p.max, p.count].join(","));
  return `${lines.join("\r\n")}\r\n`;
}

export function safeFileName(text, fallback = "export") {
  const slug = String(text || "").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[-.]+|[-.]+$/g, "").slice(0, 60);
  return slug || fallback;
}

export function formatNumber(value, unit = "") {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const text = Number(value).toFixed(2).replace(/\.?0+$/, "");
  return unit ? `${text} ${unit}` : text;
}
