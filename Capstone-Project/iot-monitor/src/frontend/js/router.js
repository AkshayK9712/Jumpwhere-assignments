import { compile, match, parseHash, buildHash } from "./route-match.js";
import * as session from "./session.js";
import { h, loading } from "./ui.js";

const NEXT_KEY = "iot.next";
let compiled = [];
let outlet = null;
let renderId = 0;
let cleanup = null;

export function start(routes, outletEl) {
  compiled = compile(routes);
  outlet = outletEl;
  window.addEventListener("hashchange", render);
  render();
}

export function navigate(path, query = {}, { replace = false } = {}) {
  const hash = buildHash(path, query);
  if (replace) {
    history.replaceState(null, "", hash);
    render();
  } else if (location.hash === hash) {
    render();
  } else {
    location.hash = hash; // triggers hashchange -> render
  }
}

/** Update the address bar (e.g. filters) without re-rendering the page. */
export function replaceQuery(query) {
  const { path } = parseHash(location.hash);
  history.replaceState(null, "", buildHash(path, query));
}

/** Where to go after login: the page the user originally asked for. */
export function consumeNext() {
  const saved = sessionStorage.getItem(NEXT_KEY);
  sessionStorage.removeItem(NEXT_KEY);
  return parseHash(saved || "#/");
}

function show(el) {
  outlet.replaceChildren(el);
  const heading = el.querySelector?.("h1");
  document.title = heading ? `${heading.textContent} · IoT Monitor` : "IoT Monitor";
  heading?.focus({ preventScroll: true }); // moves screen-reader focus to the new page
  window.scrollTo(0, 0);
}

const messageCard = (title, text) =>
  h("section", { class: "card narrow" }, h("h1", { tabindex: "-1" }, title), h("p", {}, text),
    h("a", { class: "btn", href: "#/" }, "Go to the home page"));

async function render() {
  const id = ++renderId;
  const { path, query } = parseHash(location.hash);
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  window.dispatchEvent(new CustomEvent("routechange", { detail: { path } }));

  const found = match(compiled, path);
  if (!found) return show(messageCard("Page not found", "That page does not exist."));

  const { route, params } = found;
  const user = session.getUser();
  const loggedIn = session.isLoggedIn() && user;

  if (route.access === "guest-only" && loggedIn) return navigate("/", {}, { replace: true });
  if (route.access !== "public" && route.access !== "guest-only" && !loggedIn) {
    sessionStorage.setItem(NEXT_KEY, location.hash);
    return navigate("/login", {}, { replace: true });
  }
  if (Array.isArray(route.access) && !route.access.includes(user.role)) {
    return show(messageCard("Not allowed", "Your role does not have access to this page."));
  }

  outlet.replaceChildren(loading());
  try {
    const result = await route.view({ params, query, user });
    const el = result instanceof Node ? result : result.el;
    const destroy = result instanceof Node ? null : result.destroy;
    if (id !== renderId) return destroy?.(); // the user already went somewhere else
    cleanup = destroy || null;
    show(el);
  } catch (err) {
    if (id !== renderId) return;
    if (err?.status === 401) return navigate("/login", {}, { replace: true });
    const retry = h("button", { type: "button", class: "btn", onclick: render }, "Try again");
    const back = h("a", { class: "btn", href: "#/" }, "Home");
    show(h("section", { class: "card narrow", role: "alert" },
      h("h1", { tabindex: "-1" }, err?.status === 404 ? "Not found" : "Something went wrong"),
      h("p", {}, err?.message || "Unexpected error."), h("div", { class: "row" }, retry, back)));
  }
}
