import * as api from "../api.js";
import { emptyState, errorBox, pageHeader } from "../components.js";
import { CATEGORIES, PRIORITIES, STATUSES, WRITER_ROLES } from "../constants.js";
import { debounce, formatDate, titleCase, toInt } from "../format.js";
import * as router from "../router.js";
import { confirmDialog, h, loading, pager, priorityBadge, statusBadge, toast } from "../ui.js";

const DEFAULTS = { page: 1, page_size: 20, q: "", status: "", category: "", priority: "", sort: "-created_at" };
const SORTS = [["-created_at", "Newest first"], ["created_at", "Oldest first"], ["title", "Title A–Z"], ["-title", "Title Z–A"], ["-priority", "Priority high → low"], ["priority", "Priority low → high"]];
const pick = (value, allowed) => (allowed.includes(value) ? value : "");

export default function sensorsView({ query, user }) {
  const canWrite = WRITER_ROLES.includes(user.role);
  const state = {
    page: toInt(query.page, 1),
    page_size: [10, 20, 50].includes(Number(query.page_size)) ? Number(query.page_size) : DEFAULTS.page_size,
    q: (query.q || "").slice(0, 100),
    status: pick(query.status, STATUSES),
    category: pick(query.category, CATEGORIES),
    priority: pick(query.priority, PRIORITIES),
    sort: SORTS.some(([v]) => v === query.sort) ? query.sort : DEFAULTS.sort,
  };
  let alive = true;
  const selected = new Set();
  const host = h("div", { class: "table-host", "aria-live": "polite" });
  const bulkButton = h("button", { type: "button", class: "btn btn-danger", hidden: true, onclick: bulkDelete }, "Delete selected");

  // ----- filter controls -----
  const select = (label, key, options) => h("select", { "aria-label": label, onchange: (e) => change(key, e.target.value) },
    options.map(([value, text]) => h("option", { value, selected: value === state[key] }, text)));

  const search = h("input", { type: "search", "aria-label": "Search sensors", placeholder: "Search title or description…", maxlength: 100 });
  search.value = state.q;
  search.addEventListener("input", debounce(() => change("q", search.value.trim()), 300));

  const toolbar = h("div", { class: "toolbar" }, search,
    select("Filter by status", "status", [["", "All statuses"], ...STATUSES.map((s) => [s, titleCase(s)])]),
    select("Filter by category", "category", [["", "All categories"], ...CATEGORIES.map((c) => [c, titleCase(c)])]),
    select("Filter by priority", "priority", [["", "All priorities"], ...PRIORITIES.map((p) => [p, titleCase(p)])]),
    select("Sort", "sort", SORTS));

  function change(key, value) {
    state[key] = value;
    state.page = 1;
    load();
  }

  function syncUrl() {
    const q = {};
    for (const [k, v] of Object.entries(state)) if (String(v) !== String(DEFAULTS[k])) q[k] = v;
    router.replaceQuery(q);
  }

  function updateBulk() {
    bulkButton.hidden = selected.size === 0;
    bulkButton.textContent = `Delete selected (${selected.size})`;
  }

  async function load() {
    if (!alive) return;
    syncUrl();
    selected.clear();
    updateBulk();
    host.replaceChildren(loading());
    try {
      const data = await api.get("/sensors", state);
      if (!alive) return;
      if (data.items.length === 0 && state.page > 1 && data.total > 0) {
        state.page = data.pages; // we deleted the last row of the last page
        return load();
      }
      render(data);
    } catch (err) {
      if (alive) host.replaceChildren(errorBox(err, load));
    }
  }

  function render(data) {
    if (data.total === 0) {
      const filtered = state.q || state.status || state.category || state.priority;
      host.replaceChildren(emptyState(filtered ? "No sensors match these filters." : "No sensors yet.",
        canWrite && !filtered ? h("a", { class: "btn btn-primary", href: "#/sensors/new" }, "Add a sensor") : null));
      return;
    }
    const rowChecks = [];
    const allCheck = h("input", { type: "checkbox", "aria-label": "Select all on this page", onchange: (e) => {
      rowChecks.forEach(({ box, id }) => {
        box.checked = e.target.checked;
        e.target.checked ? selected.add(id) : selected.delete(id);
      });
      updateBulk();
    } });

    const rows = data.items.map((s) => {
      const box = h("input", { type: "checkbox", "aria-label": `Select ${s.title}`, onchange: (e) => {
        e.target.checked ? selected.add(s.id) : selected.delete(s.id);
        updateBulk();
      } });
      rowChecks.push({ box, id: s.id });
      return h("tr", {},
        canWrite ? h("td", { class: "cell-check", "data-label": "Select" }, box) : null,
        h("td", { "data-label": "Title" }, h("a", { href: `#/sensors/${s.id}` }, s.title)),
        h("td", { "data-label": "Category" }, titleCase(s.category)),
        h("td", { "data-label": "Status" }, statusBadge(s.status)),
        h("td", { "data-label": "Priority" }, priorityBadge(s.priority)),
        h("td", { "data-label": "Location" }, s.metadata?.location || "—"),
        h("td", { "data-label": "Updated" }, formatDate(s.updated_at)),
        h("td", { class: "actions", "data-label": "Actions" },
          h("a", { class: "btn btn-sm", href: `#/sensors/${s.id}` }, "View"),
          canWrite ? [h("a", { class: "btn btn-sm", href: `#/sensors/${s.id}/edit` }, "Edit"),
            h("button", { type: "button", class: "btn btn-sm btn-danger", onclick: () => removeOne(s) }, "Delete")] : null));
    });

    host.replaceChildren(
      h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {},
          canWrite ? h("th", { class: "cell-check" }, allCheck) : null,
          ["Title", "Category", "Status", "Priority", "Location", "Updated", "Actions"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, rows))),
      pager({ page: data.page, pages: data.pages, total: data.total, pageSize: data.page_size,
        onPage: (p) => { state.page = p; load(); },
        onPageSize: (n) => { state.page_size = n; state.page = 1; load(); } }));
  }

  async function removeOne(sensor) {
    const ok = await confirmDialog({ title: "Delete sensor?", message: `“${sensor.title}” and all its readings will be permanently deleted.`, confirmText: "Delete", danger: true });
    if (!ok) return;
    try {
      await api.del(`/sensors/${sensor.id}`);
      toast("Sensor deleted.", "success");
      load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function bulkDelete() {
    const ids = [...selected];
    const ok = await confirmDialog({ title: `Delete ${ids.length} sensor(s)?`, message: "They and all their readings will be permanently deleted.", confirmText: "Delete all", danger: true });
    if (!ok) return;
    try {
      const result = await api.request("DELETE", "/sensors/bulk", { json: { ids } });
      toast(result.failed ? `Deleted ${result.processed}; ${result.failed} could not be deleted.` : `Deleted ${result.processed} sensor(s).`, result.failed ? "info" : "success");
      load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  load();
  const el = h("div", {},
    pageHeader("Sensors", bulkButton, canWrite ? h("a", { class: "btn btn-primary", href: "#/sensors/new" }, "+ New sensor") : null),
    toolbar, host);
  return { el, destroy: () => { alive = false; } };
}
