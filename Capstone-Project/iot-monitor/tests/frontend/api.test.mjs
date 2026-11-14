import assert from "node:assert/strict";
import test, { beforeEach } from "node:test";
import { installBrowserGlobals, json, mockFetch } from "./helpers.mjs";

installBrowserGlobals();
const session = await import("../../src/frontend/js/session.js");
const api = await import("../../src/frontend/js/api.js");

const delays = [];
api.configure({ sleep: async (ms) => void delays.push(ms) });

beforeEach(() => {
  session.clearSession();
  delays.length = 0;
});

const login = () => session.setTokens({ access_token: "A1", refresh_token: "R1" }, false);

test("sends the bearer token and parses JSON", async () => {
  login();
  const calls = mockFetch([json({ ok: true })]);
  assert.deepEqual(await api.get("/sensors", { page: 2, q: "", status: undefined }), { ok: true });
  assert.equal(calls[0].url, "/api/v1/sensors?page=2");
  assert.equal(calls[0].headers.Authorization, "Bearer A1");
});

test("auth:false does not send the token", async () => {
  login();
  const calls = mockFetch([json({})]);
  await api.get("/auth/verify-email", { token: "t" }, { auth: false });
  assert.equal(calls[0].headers.Authorization, undefined);
});

test("login form is sent url-encoded", async () => {
  const calls = mockFetch([json({ access_token: "x", refresh_token: "y" })]);
  await api.request("POST", "/auth/login", { form: { username: "a@b.co", password: "p w" }, auth: false, retries: 0 });
  assert.ok(calls[0].body instanceof URLSearchParams);
  assert.equal(calls[0].body.get("password"), "p w");
});

test("401 -> refresh -> retry with the new token", async () => {
  login();
  const calls = mockFetch([
    json({ detail: "expired" }, 401),
    json({ access_token: "A2", refresh_token: "R2", token_type: "bearer", expires_in: 900 }),
    json({ id: 1 }),
  ]);
  assert.deepEqual(await api.get("/users/me"), { id: 1 });
  assert.equal(calls[1].url, "/api/v1/auth/refresh");
  assert.equal(JSON.parse(calls[1].body).refresh_token, "R1");
  assert.equal(calls[2].headers.Authorization, "Bearer A2");
  assert.equal(session.getRefreshToken(), "R2");
});

test("parallel 401s share ONE refresh call", async () => {
  login();
  const calls = mockFetch([
    json({}, 401),
    json({}, 401),
    json({ access_token: "A2", refresh_token: "R2" }),
    json({ n: 1 }),
    json({ n: 2 }),
  ]);
  const [a, b] = await Promise.all([api.get("/sensors"), api.get("/users/me")]);
  assert.equal(a.n + b.n, 3);
  assert.equal(calls.filter((c) => c.url.endsWith("/auth/refresh")).length, 1);
});

test("failed refresh signs the user out", async () => {
  login();
  mockFetch([json({}, 401), json({ detail: "bad" }, 401)]);
  await assert.rejects(api.get("/users/me"), (e) => e.status === 401);
  assert.equal(session.isLoggedIn(), false);
});

test("a second 401 after refreshing is not retried forever", async () => {
  login();
  mockFetch([json({ detail: "no" }, 401), json({ access_token: "A2", refresh_token: "R2" }), json({ detail: "still no" }, 401)]);
  await assert.rejects(api.get("/users/me"), (e) => e.status === 401 && e.message === "still no");
});

test("GET retries 503 with back-off then succeeds", async () => {
  login();
  const calls = mockFetch([json({}, 503), json({}, 502), json({ ok: 1 })]);
  assert.deepEqual(await api.get("/sensors"), { ok: 1 });
  assert.equal(calls.length, 3);
  assert.deepEqual(delays, [300, 900]);
});

test("gives up after maxRetries", async () => {
  login();
  const calls = mockFetch([json({}, 503), json({}, 503), json({}, 503), json({ detail: "down" }, 503)]);
  await assert.rejects(api.get("/sensors"), (e) => e.status === 503);
  assert.equal(calls.length, 4); // 1 try + 3 retries
});

test("POST is NOT retried on 503 or on network errors", async () => {
  login();
  let calls = mockFetch([json({ detail: "down" }, 503)]);
  await assert.rejects(api.post("/sensors", {}), (e) => e.status === 503);
  assert.equal(calls.length, 1);

  calls = mockFetch([new TypeError("fetch failed")]);
  await assert.rejects(api.post("/sensors", {}), (e) => e.status === 0);
  assert.equal(calls.length, 1);
});

test("GET retries network errors", async () => {
  login();
  mockFetch([new TypeError("fetch failed"), json({ ok: 1 })]);
  assert.deepEqual(await api.get("/sensors"), { ok: 1 });
});

test("429 is retried for any method and honours Retry-After (capped)", async () => {
  login();
  const calls = mockFetch([json({}, 429, { "Retry-After": "2" }), json({}, 429, { "Retry-After": "60" }), json({ id: 9 }, 201)]);
  assert.deepEqual(await api.post("/sensors", { title: "x" }), { id: 9 });
  assert.equal(calls.length, 3);
  assert.deepEqual(delays, [2000, 5000]);
});

test("retries: 0 disables retrying", async () => {
  login();
  const calls = mockFetch([json({ detail: "slow down" }, 429, { "Retry-After": "1" })]);
  await assert.rejects(api.post("/auth/login", {}, { retries: 0 }), (e) => e.status === 429 && e.retryAfter === 1);
  assert.equal(calls.length, 1);
});

test("422 becomes per-field errors", async () => {
  login();
  mockFetch([json({ detail: [
    { loc: ["body", "title"], msg: "String should have at least 1 character" },
    { loc: ["body", "metadata", "thresholds"], msg: "Value error, thresholds.min must be less than or equal to thresholds.max" },
  ] }, 422)]);
  await assert.rejects(api.post("/sensors", {}), (e) => {
    assert.equal(e.status, 422);
    assert.equal(e.fieldErrors.title, "String should have at least 1 character");
    assert.equal(e.fieldErrors["metadata.thresholds"], "thresholds.min must be less than or equal to thresholds.max");
    return true;
  });
});

test("string detail becomes the message; 409 is reported", async () => {
  login();
  mockFetch([json({ detail: "Sensor was modified" }, 409)]);
  await assert.rejects(api.put("/sensors/1", {}), (e) => e.status === 409 && e.message === "Sensor was modified");
});

test("204 gives null; DELETE with a JSON body works", async () => {
  login();
  const calls = mockFetch([new Response(null, { status: 204 })]);
  assert.equal(await api.request("DELETE", "/sensors/bulk", { json: { ids: [1, 2] } }), null);
  assert.equal(calls[0].method, "DELETE");
  assert.deepEqual(JSON.parse(calls[0].body), { ids: [1, 2] });
  assert.equal(calls[0].headers["Content-Type"], "application/json");
});

test("custom headers are passed (If-Unmodified-Since)", async () => {
  login();
  const calls = mockFetch([json({})]);
  await api.put("/sensors/1", {}, { headers: { "If-Unmodified-Since": "2026-11-14T10:00:00Z" } });
  assert.equal(calls[0].headers["If-Unmodified-Since"], "2026-11-14T10:00:00Z");
});
