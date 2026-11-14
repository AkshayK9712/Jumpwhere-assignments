import * as api from "../api.js";
import { emptyState, errorBox, pageHeader } from "../components.js";
import { ROLES } from "../constants.js";
import { debounce, formatDate, titleCase, toInt } from "../format.js";
import * as router from "../router.js";
import { badge, confirmDialog, h, loading, pager, toast } from "../ui.js";

const pick = (value, allowed) => (allowed.includes(value) ? value : "");

export default function adminUsersView({ query, user: me }) {
  const state = { page: toInt(query.page, 1), page_size: 20, q: (query.q || "").slice(0, 100), role: pick(query.role, ROLES), is_active: pick(query.is_active, ["true", "false"]) };
  let alive = true;
  const host = h("div", { class: "table-host", "aria-live": "polite" });

  const search = h("input", { type: "search", "aria-label": "Search users", placeholder: "Search name or email…", maxlength: 100 });
  search.value = state.q;
  search.addEventListener("input", debounce(() => change("q", search.value.trim()), 300));
  const roleSelect = h("select", { "aria-label": "Filter by role", onchange: (e) => change("role", e.target.value) },
    [["", "All roles"], ...ROLES.map((r) => [r, titleCase(r)])].map(([v, t]) => h("option", { value: v, selected: v === state.role }, t)));
  const activeSelect = h("select", { "aria-label": "Filter by status", onchange: (e) => change("is_active", e.target.value) },
    [["", "Active and disabled"], ["true", "Active only"], ["false", "Disabled only"]].map(([v, t]) => h("option", { value: v, selected: v === state.is_active }, t)));

  function change(key, value) {
    state[key] = value;
    state.page = 1;
    load();
  }

  async function load() {
    if (!alive) return;
    const q = {};
    for (const [k, v] of Object.entries(state)) if (v !== "" && !(k === "page" && v === 1) && !(k === "page_size")) q[k] = v;
    router.replaceQuery(q);
    host.replaceChildren(loading());
    try {
      const data = await api.get("/users", state);
      if (alive) render(data);
    } catch (err) {
      if (alive) host.replaceChildren(errorBox(err, load));
    }
  }

  async function update(target, changes, successMessage) {
    try {
      await api.patch(`/users/${target.id}`, changes);
      toast(successMessage, "success");
    } catch (err) {
      toast(err.message, "error");
    }
    load(); // always reload so the table shows the truth
  }

  async function remove(target) {
    const ok = await confirmDialog({ title: "Delete user?", message: `${target.email} and all their sensors, readings and reports will be permanently deleted.`, confirmText: "Delete user", danger: true });
    if (!ok) return;
    try {
      await api.del(`/users/${target.id}`);
      toast("User deleted.", "success");
    } catch (err) {
      toast(err.message, "error");
    }
    load();
  }

  function render(data) {
    if (!data.total) return host.replaceChildren(emptyState("No users match these filters."));
    const rows = data.items.map((u) => {
      const self = u.id === me.id; // the server blocks self-demotion; we also disable the controls
      const roleControl = h("select", { "aria-label": `Role of ${u.email}`, disabled: self,
        onchange: async (e) => {
          const role = e.target.value;
          const ok = await confirmDialog({ title: "Change role?", message: `${u.email} will become ${role}.`, confirmText: "Change role" });
          if (ok) update(u, { role }, "Role updated.");
          else e.target.value = u.role;
        } }, ROLES.map((r) => h("option", { value: r, selected: r === u.role }, titleCase(r))));
      return h("tr", {},
        h("td", { "data-label": "Name" }, u.name, self ? " (you)" : ""),
        h("td", { "data-label": "Email" }, u.email),
        h("td", { "data-label": "Role" }, roleControl),
        h("td", { "data-label": "Status" },
          badge(u.is_active ? "active" : "disabled", u.is_active ? "success" : "danger"), " ",
          u.email_verified ? null : badge("unverified", "warn")),
        h("td", { "data-label": "Last login" }, formatDate(u.last_login)),
        h("td", { class: "actions", "data-label": "Actions" },
          h("button", { type: "button", class: "btn btn-sm", disabled: self,
            onclick: () => update(u, { is_active: !u.is_active }, u.is_active ? "User disabled." : "User enabled.") }, u.is_active ? "Disable" : "Enable"),
          h("button", { type: "button", class: "btn btn-sm btn-danger", disabled: self, onclick: () => remove(u) }, "Delete")));
    });
    host.replaceChildren(
      h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["Name", "Email", "Role", "Status", "Last login", "Actions"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, rows))),
      pager({ page: data.page, pages: data.pages, total: data.total, pageSize: data.page_size,
        onPage: (p) => { state.page = p; load(); }, onPageSize: (n) => { state.page_size = n; state.page = 1; load(); } }));
  }

  load();
  return { el: h("div", {}, pageHeader("User management"), h("div", { class: "toolbar" }, search, roleSelect, activeSelect), host), destroy: () => { alive = false; } };
}
