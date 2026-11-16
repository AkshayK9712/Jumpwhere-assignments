import * as api from "../api.js";
import { banner, emptyState, errorBox, pageHeader } from "../components.js";
import { CATEGORIES, WRITER_ROLES } from "../constants.js";
import { formatDate, localInputToIso, titleCase } from "../format.js";
import { applyErrors, badge, confirmDialog, field, h, loading, pager, saveBlob, setBusy, toast } from "../ui.js";

const TEMPLATES = [
  { value: "summary", label: "Summary: one row per sensor (min, avg, max, alerts)" },
  { value: "detailed", label: "Detailed: summary plus every reading" },
  { value: "alerts", label: "Alerts: only readings outside thresholds" },
];
const PERIODS = [["24h", "Last 24 hours", 24], ["7d", "Last 7 days", 168], ["30d", "Last 30 days", 720], ["custom", "Custom range", 0]];
const STATUS_KIND = { ready: "success", pending: "info", failed: "danger" };

export default async function reportsView({ user }) {
  const canWrite = WRITER_ROLES.includes(user.role);
  let alive = true;
  let pollTimer = null;
  let page = 1;

  const sensors = canWrite ? (await api.get("/sensors", { page_size: 100, sort: "title" })).items : [];

  // ---------- list areas ----------
  const scheduleHost = h("div", { "aria-live": "polite" });
  const reportHost = h("div", { "aria-live": "polite" });

  function download(report) {
    return async () => {
      try {
        const { blob, filename } = await api.request("GET", `/reports/${report.id}/download`, { blob: true });
        saveBlob(blob, filename || `${report.name}.${report.format}`);
      } catch (err) {
        toast(err.message, "error");
      }
    };
  }

  async function remove(report, isSchedule) {
    const ok = await confirmDialog({
      title: isSchedule ? "Stop this schedule?" : "Delete report?",
      message: isSchedule ? `“${report.name}” will no longer be generated. Reports it already made are kept.` : `“${report.name}” and its file will be deleted.`,
      confirmText: isSchedule ? "Stop schedule" : "Delete", danger: true,
    });
    if (!ok) return;
    try {
      await api.del(`/reports/${report.id}`);
      toast(isSchedule ? "Schedule stopped." : "Report deleted.", "success");
      loadLists();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function loadLists() {
    clearTimeout(pollTimer);
    try {
      const [schedules, reports] = await Promise.all([
        api.get("/reports", { scheduled: true, page_size: 50 }),
        api.get("/reports", { scheduled: false, page, page_size: 10 }),
      ]);
      if (!alive) return;
      renderSchedules(schedules.items);
      renderReports(reports);
      if (reports.items.some((r) => r.status === "pending")) {
        pollTimer = setTimeout(loadLists, 2500); // keep checking while a report is being built
      }
    } catch (err) {
      if (alive) {
        scheduleHost.replaceChildren(loading());
        reportHost.replaceChildren(errorBox(err, loadLists));
      }
    }
  }

  function renderSchedules(items) {
    if (!items.length) return scheduleHost.replaceChildren(emptyState("No scheduled reports."));
    scheduleHost.replaceChildren(h("div", { class: "table-wrap" }, h("table", { class: "table" },
      h("thead", {}, h("tr", {}, ["Name", "Repeats", "Format", "Next run", "Last run", "Actions"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, items.map((r) => h("tr", {},
        h("td", { "data-label": "Name" }, r.name),
        h("td", { "data-label": "Repeats" }, titleCase(r.query_params?.schedule?.frequency || "")),
        h("td", { "data-label": "Format" }, r.format.toUpperCase()),
        h("td", { "data-label": "Next run" }, formatDate(r.next_run_at)),
        h("td", { "data-label": "Last run" }, formatDate(r.last_run_at)),
        h("td", { class: "actions", "data-label": "Actions" },
          canWrite ? h("button", { type: "button", class: "btn btn-sm btn-danger", onclick: () => remove(r, true) }, "Stop") : null)))))));
  }

  function renderReports(data) {
    if (!data.total) return reportHost.replaceChildren(emptyState("No reports yet. Generate one above."));
    reportHost.replaceChildren(
      h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["Name", "Format", "Status", "Created", "Expires", "Actions"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, data.items.map((r) => h("tr", {},
          h("td", { "data-label": "Name" }, r.name, r.source_id ? h("span", { class: "muted" }, " (scheduled)") : null),
          h("td", { "data-label": "Format" }, r.format.toUpperCase()),
          h("td", { "data-label": "Status" }, badge(r.status, STATUS_KIND[r.status] || "muted")),
          h("td", { "data-label": "Created" }, formatDate(r.created_at)),
          h("td", { "data-label": "Expires" }, formatDate(r.expires_at)),
          h("td", { class: "actions", "data-label": "Actions" },
            h("button", { type: "button", class: "btn btn-sm btn-primary", disabled: r.status !== "ready", onclick: download(r) }, "Download"),
            canWrite ? h("button", { type: "button", class: "btn btn-sm btn-danger", onclick: () => remove(r, false) }, "Delete") : null)))))),
      pager({ page: data.page, pages: data.pages, total: data.total, pageSize: data.page_size,
        onPage: (p) => { page = p; loadLists(); }, onPageSize: () => {} }));
  }

  // ---------- create form ----------
  let form = h("div", { class: "banner banner-info" }, "Guest accounts can view and download reports but not create them.");
  if (canWrite) {
    const f = {
      name: field({ label: "Report name", name: "name", required: true, maxlength: 150, value: "Plant report" }),
      format: field({ label: "Format", name: "format", value: "pdf", options: [{ value: "pdf", label: "PDF" }, { value: "csv", label: "CSV (spreadsheet)" }] }),
      template: field({ label: "Contents", name: "template", value: "summary", options: TEMPLATES }),
      category: field({ label: "Category", name: "category", value: "", options: [{ value: "", label: "All categories" }, ...CATEGORIES.map((c) => ({ value: c, label: titleCase(c) }))] }),
      period: field({ label: "Period", name: "period", value: "24h", options: PERIODS.map(([value, label]) => ({ value, label })) }),
      from: field({ label: "From", name: "from", type: "datetime-local" }),
      to: field({ label: "To", name: "to", type: "datetime-local" }),
      frequency: field({ label: "Repeat", name: "frequency", value: "daily", options: [["daily", "Every day (covers the last 24 hours)"], ["weekly", "Every week (last 7 days)"], ["monthly", "Every 30 days (last 30 days)"]].map(([value, label]) => ({ value, label })) }),
    };
    const sensorSelect = h("select", { id: "report-sensors", multiple: true, size: 6, "aria-describedby": "report-sensors-hint" },
      sensors.map((s) => h("option", { value: s.id }, s.title)));
    const scheduled = h("input", { type: "checkbox", id: "report-scheduled" });
    const emailMe = h("input", { type: "checkbox", id: "report-email", checked: true });
    const customBox = h("div", { class: "grid-2", hidden: true }, f.from.el, f.to.el);
    const rangeBox = h("div", { class: "stack" }, f.period.el, customBox);
    const scheduleBox = h("div", { class: "stack", hidden: true }, f.frequency.el,
      h("label", { class: "check", for: "report-email" }, emailMe, " Email me when each report is ready"));
    const notice = h("div");
    const submit = h("button", { type: "submit", class: "btn btn-primary" }, "Generate report");

    const sync = () => {
      customBox.hidden = f.period.value !== "custom";
      rangeBox.hidden = scheduled.checked;
      scheduleBox.hidden = !scheduled.checked;
      submit.textContent = scheduled.checked ? "Create schedule" : "Generate report";
    };
    f.period.input.addEventListener("change", sync);
    scheduled.addEventListener("change", sync);

    form = h("form", {
      class: "stack", novalidate: true,
      onsubmit: async (e) => {
        e.preventDefault();
        notice.replaceChildren();
        const errors = {};
        const name = f.name.value.trim();
        if (!name) errors.name = "Name is required.";
        const query = { template: f.template.value };
        const ids = [...sensorSelect.selectedOptions].map((o) => Number(o.value));
        if (ids.length) query.sensor_ids = ids;
        if (f.category.value) query.category = f.category.value;

        if (!scheduled.checked) {
          const chosen = PERIODS.find(([value]) => value === f.period.value);
          if (f.period.value === "custom") {
            const from = localInputToIso(f.from.value);
            const to = localInputToIso(f.to.value);
            if (!from) errors.from = "Choose a start time.";
            if (!to) errors.to = "Choose an end time.";
            if (from && to && from >= to) errors.to = "The end must be after the start.";
            Object.assign(query, { from, to });
          } else {
            const now = new Date();
            query.from = new Date(now.getTime() - chosen[2] * 3600e3).toISOString();
            query.to = now.toISOString();
          }
        }
        applyErrors({ name: f.name, from: f.from, to: f.to }, errors);
        if (Object.keys(errors).length) return;

        const body = { name, format: f.format.value, query_params: query, scheduled: scheduled.checked };
        if (scheduled.checked) body.schedule = { frequency: f.frequency.value, email: emailMe.checked };

        setBusy(submit, true, "Working…");
        try {
          await api.post("/reports", body);
          toast(scheduled.checked ? "Schedule created. The first report is being built." : "Report requested. It will be ready in a moment.", "success");
          page = 1;
          loadLists();
        } catch (err) {
          const rest = applyErrors({ name: f.name }, err.fieldErrors || {});
          notice.replaceChildren(banner(err.fieldErrors && Object.keys(err.fieldErrors).length ? Object.values(err.fieldErrors).join(" ") : err.message));
          void rest;
        } finally {
          setBusy(submit, false);
          sync();
        }
      },
    },
    f.name.el, h("div", { class: "grid-2" }, f.format.el, f.template.el),
    h("div", { class: "field" }, h("label", { for: "report-sensors" }, "Sensors"), sensorSelect,
      h("p", { class: "hint", id: "report-sensors-hint" }, "Hold Ctrl (or Cmd) to pick several. Leave empty to include all your sensors.")),
    f.category.el, rangeBox,
    h("label", { class: "check", for: "report-scheduled" }, scheduled, " Repeat automatically (scheduled report)"),
    scheduleBox, notice, submit);
  }

  loadLists();
  const el = h("div", {}, pageHeader("Reports"),
    canWrite ? h("section", { class: "card" }, h("h2", {}, "New report"), form) : form,
    h("section", { class: "card" }, h("h2", {}, "Scheduled reports"), scheduleHost),
    h("section", { class: "card" }, h("h2", {}, "Generated reports"), reportHost));

  return { el, destroy: () => { alive = false; clearTimeout(pollTimer); } };
}
