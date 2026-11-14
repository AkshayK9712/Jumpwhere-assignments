// Pure routing helpers (no DOM).

/** "/sensors/:id/edit" -> regex + parameter names */
export function compile(routes) {
  return routes.map((route) => {
    const names = [];
    const pattern = route.path.replace(/\/:([A-Za-z_]+)/g, (_, name) => {
      names.push(name);
      return "/([^/]+)";
    });
    return { ...route, names, re: new RegExp(`^${pattern}/?$`) };
  });
}

export function match(compiled, path) {
  for (const route of compiled) {
    const m = route.re.exec(path);
    if (m) {
      const params = {};
      route.names.forEach((name, i) => (params[name] = decodeURIComponent(m[i + 1])));
      return { route, params };
    }
  }
  return null;
}

/** "#/sensors?page=2" -> { path: "/sensors", query: { page: "2" } } */
export function parseHash(hash) {
  let h = hash || "";
  if (h.startsWith("#")) h = h.slice(1);
  if (!h.startsWith("/")) h = `/${h}`;
  const qIndex = h.indexOf("?");
  const path = qIndex === -1 ? h : h.slice(0, qIndex);
  const qs = qIndex === -1 ? "" : h.slice(qIndex + 1);
  return { path: path || "/", query: Object.fromEntries(new URLSearchParams(qs)) };
}

export function buildHash(path, query = {}) {
  const pairs = Object.entries(query).filter(([, v]) => v !== "" && v !== null && v !== undefined);
  const qs = new URLSearchParams(pairs).toString();
  return `#${path}${qs ? `?${qs}` : ""}`;
}
