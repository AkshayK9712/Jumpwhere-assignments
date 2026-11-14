import assert from "node:assert/strict";
import test from "node:test";
import {
  parseOptionalNumber, passwordProblems, validateEmail, validateName, validatePassword,
  validateProfileForm, validateReadingForm, validateSensorForm,
} from "../../src/frontend/js/validators.js";

test("email", () => {
  assert.equal(validateEmail("a@b.co"), "");
  assert.notEqual(validateEmail(""), "");
  assert.notEqual(validateEmail("nope"), "");
  assert.notEqual(validateEmail("a b@c.com"), "");
});

test("password rules match the server", () => {
  assert.deepEqual(passwordProblems("Str0ng!Pass"), []);
  assert.deepEqual(passwordProblems("password"), ["an uppercase letter", "a digit", "a symbol"]);
  assert.match(validatePassword("short"), /Password needs/);
  assert.equal(validatePassword("Str0ng!Pass"), "");
  assert.match(validatePassword("A1!a".repeat(30)), /72/);
});

test("name", () => {
  assert.equal(validateName("Ann"), "");
  assert.notEqual(validateName("   "), "");
  assert.notEqual(validateName("x".repeat(121)), "");
});

test("parseOptionalNumber", () => {
  assert.equal(parseOptionalNumber(""), null);
  assert.equal(parseOptionalNumber("  "), null);
  assert.equal(parseOptionalNumber("12.5"), 12.5);
  assert.equal(parseOptionalNumber("0"), 0);
  assert.ok(Number.isNaN(parseOptionalNumber("abc")));
});

const goodSensor = { title: "Boiler", description: "", category: "temperature", status: "active", priority: "medium",
  factory: "", location: "", unit: "", min: "", max: "" };

test("valid sensor form has no errors", () => {
  assert.deepEqual(validateSensorForm(goodSensor), {});
});

test("sensor form errors", () => {
  const e = validateSensorForm({ ...goodSensor, title: "  ", category: "", min: "10", max: "5", unit: "x".repeat(21) });
  assert.ok(e.title && e.category && e["metadata.thresholds.max"] && e["metadata.unit"]);
  assert.ok(validateSensorForm({ ...goodSensor, min: "abc" })["metadata.thresholds.min"]);
  assert.deepEqual(validateSensorForm({ ...goodSensor, min: "5", max: "5" }), {});
  assert.ok(validateSensorForm({ ...goodSensor, title: "x".repeat(151) }).title);
});

test("reading form", () => {
  const now = new Date("2026-11-14T12:00:00Z");
  assert.deepEqual(validateReadingForm({ value: "71.5", recorded_at: "" }, now), {});
  assert.ok(validateReadingForm({ value: "", recorded_at: "" }, now).value);
  assert.ok(validateReadingForm({ value: "abc" }, now).value);
  assert.ok(validateReadingForm({ value: "1", recorded_at: "2026-11-14T15:00:00Z" }, now).recorded_at);
  assert.deepEqual(validateReadingForm({ value: "1", recorded_at: "2026-11-14T11:00:00Z" }, now), {});
});

test("profile form", () => {
  assert.deepEqual(validateProfileForm({ avatar_url: "https://x.io/a.png", phone: "+91 98765 43210", language: "en-IN", timezone: "Asia/Kolkata" }), {});
  const e = validateProfileForm({ avatar_url: "javascript:alert(1)", phone: "call me", language: "english", timezone: "bad zone!" });
  assert.ok(e.avatar_url && e.phone && e.language && e.timezone);
});
