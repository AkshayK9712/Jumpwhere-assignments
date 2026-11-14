import * as api from "../api.js";
import { emptyState, errorBox, pageHeader } from "../components.js";
import { debounce, formatDate, toInt } from "../format.js";
import * as router from "../router.js";
import { h, loading, pager } from "../ui.js";

export default function adminLogsView({ query }) {
  const state = { page: toInt(query.page, 1), page_size: 20, action: (query.action || "").slice(0, 50), entity_type: (query.entity_type || "").slice(0, 50), user_id: /^\d+$/.test(query.user_id || "") ? query.user_id : "" };
  let alive = true;
  const host = h("div", { class: "table-host", "aria-live": "polite" });

  const input = (label, key, placeholder) => {
    const el = h("input", { type: "search", "aria-label": label, placeholder, maxlength: 50 });
    el.value = state[key];
    el.addEventListener("input", debounce(() => { state[key] = el.value.trim(); state.page = 1; load(); }, 300));
    return el;
  };
  const toolbar = h("div", { class: "toolbar" }, input("Filter by action", "action", "Action, e.g. sensor.create"),
    input("Filter by entity type", "entity_type", "Entity, e.g. sensor"), input("Filter by user id", "user_id", "User id"));

  async function load() {
    if (!alive) return;
    const q = {};
    for (const [k, v] of Object.entries(state)) if (v !== "" && k !== "page_size" && !(k === "page" && v === 1)) q[k] = v;
    router.replaceQuery(q);
    host.replaceChildren(loading());
    try {
      const data = await api.get("/admin/activity-logs", state);
      if (alive) render(data);
    } catch (err) {
      if (alive) host.replaceChildren(errorBox(err, load));
    }
  }

  function render(data) {
    if (!data.total) return host.replaceChildren(emptyState("No log entries match."));
    const rows = data.items.map((l) => {
      const details = Object.keys(l.details || {}).length ? JSON.stringify(l.details) : "";
      return h("tr", {},
        h("td", { "data-label": "When" }, formatDate(l.created_at)),
        h("td", { "data-label": "Action" }, h("code", {}, l.action)),
        h("td", { "data-label": "User" }, l.user_id ?? "—"),
        h("td", { "data-label": "Entity" }, l.entity_type ? `${l.entity_type} #${l.entity_id ?? ""}` : "—"),
        h("td", { "data-label": "IP" }, l.ip_address || "—"),
        h("td", { class: "details-cell", "data-label": "Details" }, details ? h("code", {}, details.length > 120 ? `${details.slice(0, 120)}…` : details) : "—"));
    });
    host.replaceChildren(
      h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["When", "Action", "User", "Entity", "IP", "Details"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, rows))),
      pager({ page: data.page, pages: data.pages, total: data.total, pageSize: data.page_size,
        onPage: (p) => { state.page = p; load(); }, onPageSize: (n) => { state.page_size = n; state.page = 1; load(); } }));
  }

  load();
  return { el: h("div", {}, pageHeader("Audit log"), toolbar, host), destroy: () => { alive = false; } };
}
