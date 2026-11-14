import assert from "node:assert/strict";
import test from "node:test";
import { debounce, describeThresholds, formatDate, localInputToIso, parseApiDate, titleCase, toInt } from "../../src/frontend/js/format.js";

test("naive API dates are treated as UTC", () => {
  assert.equal(parseApiDate("2026-11-14T10:00:00").toISOString(), "2026-11-14T10:00:00.000Z");
  assert.equal(parseApiDate("2026-11-14T10:00:00.123456").toISOString(), "2026-11-14T10:00:00.123Z");
});

test("dates with a zone are respected", () => {
  assert.equal(parseApiDate("2026-11-14T10:00:00+05:30").toISOString(), "2026-11-14T04:30:00.000Z");
  assert.equal(parseApiDate("2026-11-14T10:00:00Z").toISOString(), "2026-11-14T10:00:00.000Z");
});

test("bad or empty dates", () => {
  assert.equal(parseApiDate(""), null);
  assert.equal(parseApiDate("nonsense"), null);
  assert.equal(formatDate(null), "—");
  assert.notEqual(formatDate("2026-11-14T10:00:00Z"), "—");
});

test("titleCase, toInt, localInputToIso", () => {
  assert.equal(titleCase("temperature"), "Temperature");
  assert.equal(titleCase(undefined), "");
  assert.equal(toInt("3", 1), 3);
  assert.equal(toInt("0", 1), 1);
  assert.equal(toInt("abc", 20), 20);
  assert.equal(localInputToIso(""), null);
  assert.match(localInputToIso("2026-11-14T10:30"), /^\d{4}-\d\d-\d\dT/);
});

test("describeThresholds", () => {
  assert.equal(describeThresholds({ min: 1, max: 5 }), "1 to 5");
  assert.equal(describeThresholds({ max: 5 }), "at most 5");
  assert.equal(describeThresholds({ min: 0 }), "at least 0");
  assert.equal(describeThresholds(null), "—");
});

test("debounce only fires the last call", async () => {
  const calls = [];
  const d = debounce((x) => calls.push(x), 20);
  d(1); d(2); d(3);
  await new Promise((r) => setTimeout(r, 60));
  assert.deepEqual(calls, [3]);
});
