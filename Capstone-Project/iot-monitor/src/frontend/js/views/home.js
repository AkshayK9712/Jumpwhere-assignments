import * as api from "../api.js";
import { emptyState, pageHeader } from "../components.js";
import { formatDate, titleCase } from "../format.js";
import { h, statusBadge } from "../ui.js";

export default async function homeView({ user }) {
  const statuses = [["All sensors", ""], ["Active", "active"], ["Inactive", "inactive"], ["Faulty", "faulty"]];
  const [counts, recent] = await Promise.all([
    Promise.all(statuses.map(([, status]) => api.get("/sensors", { page_size: 1, status }).then((r) => r.total))),
    api.get("/sensors", { page_size: 5, sort: "-created_at" }),
  ]);

  const cards = statuses.map(([label, status], i) =>
    h("a", { class: `stat stat-${status || "all"}`, href: status ? `#/sensors?status=${status}` : "#/sensors" },
      h("span", { class: "stat-value" }, counts[i]), h("span", { class: "stat-label" }, label)));

  const list = recent.items.length
    ? h("ul", { class: "list" }, recent.items.map((s) =>
      h("li", {}, h("a", { href: `#/sensors/${s.id}` }, s.title), " ", statusBadge(s.status),
        h("span", { class: "muted" }, ` · ${titleCase(s.category)} · added ${formatDate(s.created_at)}`))))
    : emptyState("No sensors yet.", user.role !== "guest" ? h("a", { class: "btn btn-primary", href: "#/sensors/new" }, "Add your first sensor") : null);

  return h("div", {},
    pageHeader(`Welcome, ${user.name}`),
    h("div", { class: "stats" }, cards),
    h("section", { class: "card" }, h("h2", {}, "Recently added"), list),
    h("p", { class: "muted" }, "Live charts and reports are coming soon."));
}
