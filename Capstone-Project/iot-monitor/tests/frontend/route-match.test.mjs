import assert from "node:assert/strict";
import test from "node:test";
import { buildHash, compile, match, parseHash } from "../../src/frontend/js/route-match.js";

const routes = compile([
  { path: "/", name: "home" },
  { path: "/sensors", name: "list" },
  { path: "/sensors/new", name: "new" },
  { path: "/sensors/:id", name: "detail" },
  { path: "/sensors/:id/edit", name: "edit" },
  { path: "/admin/users", name: "users" },
]);

test("static and parameterized routes", () => {
  assert.equal(match(routes, "/").route.name, "home");
  assert.equal(match(routes, "/sensors").route.name, "list");
  assert.equal(match(routes, "/sensors/").route.name, "list"); // trailing slash
  const m = match(routes, "/sensors/42/edit");
  assert.equal(m.route.name, "edit");
  assert.deepEqual(m.params, { id: "42" });
});

test("'new' is not read as an id (order matters)", () => {
  assert.equal(match(routes, "/sensors/new").route.name, "new");
  assert.equal(match(routes, "/sensors/7").route.name, "detail");
});

test("unknown paths do not match", () => {
  assert.equal(match(routes, "/nope"), null);
  assert.equal(match(routes, "/sensors/1/2/3"), null);
});

test("parseHash", () => {
  assert.deepEqual(parseHash(""), { path: "/", query: {} });
  assert.deepEqual(parseHash("#/"), { path: "/", query: {} });
  assert.deepEqual(parseHash("#/sensors?page=2&q=boiler%20a"), { path: "/sensors", query: { page: "2", q: "boiler a" } });
  assert.deepEqual(parseHash("#/verify?token=abc.def-ghi_jkl"), { path: "/verify", query: { token: "abc.def-ghi_jkl" } });
  assert.deepEqual(parseHash("sensors"), { path: "/sensors", query: {} });
});

test("buildHash drops empty values", () => {
  assert.equal(buildHash("/sensors", { page: 2, q: "", status: undefined }), "#/sensors?page=2");
  assert.equal(buildHash("/"), "#/");
});
