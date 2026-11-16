import assert from "node:assert/strict";
import test from "node:test";
import { formatNumber, pickInterval, resolveRange, safeFileName, seriesStats, seriesToCsv } from "../../src/frontend/js/dashboard-utils.js";

const NOW = new Date("2026-11-14T12:00:00Z");

test("preset ranges are live and end now", () => {
  const r = resolveRange("6h", "", "", NOW);
  assert.equal(r.live, true);
  assert.equal(r.to.getTime(), NOW.getTime());
  assert.equal(r.to - r.from, 6 * 3600e3);
  assert.equal(resolveRange("7d", "", "", NOW).to - resolveRange("7d", "", "", NOW).from, 7 * 86400e3);
});

test("unknown preset falls back to 24 hours", () => {
  const r = resolveRange("bogus", "", "", NOW);
  assert.equal(r.to - r.from, 24 * 3600e3);
});

test("custom ranges are fixed and validated", () => {
  const ok = resolveRange("custom", "2026-11-01T00:00", "2026-11-02T00:00", NOW);
  assert.equal(ok.live, false);
  assert.ok(ok.from < ok.to);
  assert.ok(resolveRange("custom", "", "", NOW).error);
  assert.ok(resolveRange("custom", "nonsense", "2026-11-02T00:00", NOW).error);
  assert.match(resolveRange("custom", "2026-11-02T00:00", "2026-11-01T00:00", NOW).error, /before/);
  assert.match(resolveRange("custom", "2024-01-01T00:00", "2026-01-01T00:00", NOW).error, /366/);
});

test("interval choice keeps charts readable and below the server limit of 2000 points", () => {
  assert.equal(pickInterval(3600e3), "minute");
  assert.equal(pickInterval(6 * 3600e3), "minute");
  assert.equal(pickInterval(24 * 3600e3), "hour");
  assert.equal(pickInterval(14 * 86400e3), "hour");
  assert.equal(pickInterval(30 * 86400e3), "day");
  for (const [ms, interval, unit] of [[6 * 3600e3, "minute", 60e3], [14 * 86400e3, "hour", 3600e3], [366 * 86400e3, "day", 86400e3]]) {
    assert.equal(pickInterval(ms), interval);
    assert.ok(ms / unit + 1 <= 2000);
  }
});

test("seriesStats weights the average by reading count", () => {
  assert.equal(seriesStats([]), null);
  const s = seriesStats([{ avg: 10, min: 5, max: 20, count: 1 }, { avg: 20, min: 15, max: 30, count: 3 }]);
  assert.deepEqual(s, { count: 4, min: 5, max: 30, avg: 17.5 });
});

test("seriesToCsv", () => {
  const csv = seriesToCsv([{ bucket: "2026-11-14T10:00:00Z", avg: 1.5, min: 1, max: 2, count: 4 }], { unit: "C" });
  assert.equal(csv, "bucket_utc,avg (C),min (C),max (C),readings\r\n2026-11-14T10:00:00.000Z,1.5,1,2,4\r\n");
  assert.ok(seriesToCsv([], {}).startsWith("bucket_utc,avg,min,max,readings"));
});

test("safeFileName and formatNumber", () => {
  assert.equal(safeFileName("Boiler / Room #1"), "Boiler-Room-1");
  assert.equal(safeFileName("???"), "export");
  assert.equal(safeFileName("../../etc/passwd"), "etc-passwd");
  assert.equal(formatNumber(75.5, "°C"), "75.5 °C");
  assert.equal(formatNumber(3), "3");
  assert.equal(formatNumber(null), "—");
  assert.equal(formatNumber(2.456), "2.46");
});
