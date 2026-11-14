import assert from "node:assert/strict";
import test, { beforeEach } from "node:test";
import { installBrowserGlobals } from "./helpers.mjs";

installBrowserGlobals();
const session = await import("../../src/frontend/js/session.js");

beforeEach(() => session.clearSession());

test("remember me -> localStorage only", () => {
  session.setTokens({ access_token: "a", refresh_token: "r" }, true);
  assert.ok(localStorage.getItem("iot.session"));
  assert.equal(sessionStorage.getItem("iot.session"), null);
  assert.equal(session.getAccessToken(), "a");
});

test("no remember me -> sessionStorage only", () => {
  session.setTokens({ access_token: "a", refresh_token: "r" }, false);
  assert.equal(localStorage.getItem("iot.session"), null);
  assert.ok(sessionStorage.getItem("iot.session"));
});

test("rotating tokens keeps the remember-me choice", () => {
  session.setTokens({ access_token: "a", refresh_token: "r" }, true);
  session.setTokens({ access_token: "b", refresh_token: "s" });
  assert.ok(localStorage.getItem("iot.session"));
  assert.equal(JSON.parse(localStorage.getItem("iot.session")).access_token, "b");
});

test("clearSession wipes everything and notifies listeners", () => {
  let events = 0;
  const off = session.onChange(() => events++);
  session.setTokens({ access_token: "a", refresh_token: "r" }, true);
  session.setUser({ id: 1, role: "admin" });
  assert.ok(session.hasRole("admin"));
  assert.ok(!session.hasRole("guest"));
  session.clearSession();
  assert.equal(session.isLoggedIn(), false);
  assert.equal(session.getUser(), null);
  assert.equal(localStorage.getItem("iot.session"), null);
  assert.ok(events >= 3);
  off();
});
