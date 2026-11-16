import * as api from "../api.js";
import { renderDonut, renderLineChart } from "../charts.js";
import { emptyState, pageHeader } from "../components.js";
import { CATEGORIES, WRITER_ROLES } from "../constants.js";
import { POLL_MS, RANGE_PRESETS, formatNumber, pickInterval, resolveRange, safeFileName, seriesStats, seriesToCsv } from "../dashboard-utils.js";
import { loadD3 } from "../d3-loader.js";
import { formatDate, titleCase } from "../format.js";
import * as router from "../router.js";
import { banner, field, h, saveBlob, toast } from "../ui.js";

export default async function dashboardView({ query, user }) {
  const sensors = (await api.get("/sensors", { page_size: 100, sort: "title" })).items;
  const canWrite = WRITER_ROLES.includes(user.role);

  const state = {
    sensor: sensors.some((s) => String(s.id) === query.sensor) ? query.sensor : sensors[0] ? String(sensors[0].id) : "",
    range: RANGE_PRESETS.some((p) => p.id === query.range) ? query.range : "24h",
    category: CATEGORIES.includes(query.category) ? query.category : "",
    from: query.from || "",
    to: query.to || "",
    paused: false,
  };
  let alive = true;
  let inFlight = false;
  let failures = 0;
  let d3 = null;
  let summary = null;
  let series = null;
  let lastWidth = 0;

  if (sensors.length === 0) {
    return h("div", {}, pageHeader("Dashboard"),
      h("section", { class: "card" }, emptyState("There are no sensors to chart yet.",
        canWrite ? h("a", { class: "btn btn-primary", href: "#/sensors/new" }, "Add a sensor") : null)));
  }

  // ---------- controls ----------
  const sensorField = field({ label: "Sensor", name: "sensor", value: state.sensor,
    options: sensors.map((s) => ({ value: String(s.id), label: s.title })) });
  const rangeField = field({ label: "Period", name: "range", value: state.range, options: RANGE_PRESETS.map((p) => ({ value: p.id, label: p.label })) });
  const fromField = field({ label: "From", name: "from", type: "datetime-local", value: state.from });
  const toField = field({ label: "To", name: "to", type: "datetime-local", value: state.to });
  const categoryField = field({ label: "Category (counts)", name: "category", value: state.category,
    options: [{ value: "", label: "All categories" }, ...CATEGORIES.map((c) => ({ value: c, label: titleCase(c) }))] });
  const customBox = h("div", { class: "custom-range", hidden: state.range !== "custom" }, fromField.el, toField.el);

  const pauseButton = h("button", { type: "button", class: "btn btn-sm", "aria-pressed": "false" }, "Pause live updates");
  const exportButton = h("button", { type: "button", class: "btn btn-sm" }, "Export CSV");
  const status = h("span", { class: "muted live-status", "aria-live": "off" }, "Loading…");
  const problem = h("div");

  // ---------- output areas ----------
  const statsHost = h("div", { class: "stats" });
  const lineHost = h("div", { class: "chart-host", "aria-busy": "true" });
  const donutHost = h("div", { class: "chart-host" });
  const seriesFacts = h("p", { class: "muted" });
  const tableHost = h("details", { class: "data-table" }, h("summary", {}, "View chart data as a table"));
  const chartWarning = h("div");

  function syncUrl() {
    const q = { sensor: state.sensor, range: state.range === "24h" ? "" : state.range, category: state.category };
    if (state.range === "custom") Object.assign(q, { from: state.from, to: state.to });
    router.replaceQuery(q);
  }

  function renderStats() {
    if (!summary) return;
    const card = (value, label, cls, href) => h("a", { class: `stat ${cls}`, href },
      h("span", { class: "stat-value" }, value), h("span", { class: "stat-label" }, label));
    statsHost.replaceChildren(
      card(summary.total_sensors, "Sensors", "stat-all", "#/sensors"),
      card(summary.active_sensors, "Active", "stat-active", "#/sensors?status=active"),
      card(summary.faulty_sensors, "Faulty", "stat-faulty", "#/sensors?status=faulty"),
      card(summary.readings_in_range, "Readings in period", "stat-readings", "#/sensors"));
  }

  function renderSeriesFacts() {
    const stats = series && seriesStats(series.points);
    seriesFacts.textContent = stats
      ? `${series.title}: ${stats.count} readings · min ${formatNumber(stats.min, series.unit)} · avg ${formatNumber(stats.avg, series.unit)} · max ${formatNumber(stats.max, series.unit)}`
      : series ? `${series.title}: no readings in this period.` : "";
    exportButton.disabled = !stats;
  }

  function renderTable() {
    tableHost.replaceChildren(h("summary", {}, "View chart data as a table"));
    if (!series || !series.points.length) return;
    const rows = series.points.slice(-50).reverse().map((p) => h("tr", {},
      h("td", { "data-label": "Time" }, formatDate(p.bucket)), h("td", { "data-label": "Average" }, formatNumber(p.avg, series.unit)),
      h("td", { "data-label": "Min" }, formatNumber(p.min, series.unit)), h("td", { "data-label": "Max" }, formatNumber(p.max, series.unit)),
      h("td", { "data-label": "Readings" }, p.count)));
    tableHost.append(h("p", { class: "hint" }, "Newest 50 points."), h("div", { class: "table-wrap" }, h("table", { class: "table" },
      h("thead", {}, h("tr", {}, ["Time", "Average", "Min", "Max", "Readings"].map((t) => h("th", { scope: "col" }, t)))), h("tbody", {}, rows))));
  }

  function redraw() {
    renderStats();
    renderSeriesFacts();
    renderTable();
    if (!d3) return; // charts appear as soon as D3 has loaded
    if (series) {
      lastWidth = lineHost.clientWidth;
      const range = resolveRange(state.range, state.from, state.to);
      renderLineChart(lineHost, d3, { points: series.points, unit: series.unit || "", thresholds: series.thresholds,
        from: new Date(series.range_from), to: range.live ? new Date() : new Date(series.range_to) });
    }
    if (summary) {
      renderDonut(donutHost, d3, Object.entries(summary.sensors_by_category).map(([label, value]) => ({ label: titleCase(label), value })), { centerLabel: "sensors" });
    }
    lineHost.setAttribute("aria-busy", "false");
  }

  async function refresh(quiet = false) {
    if (!alive || inFlight) return;
    const range = resolveRange(state.range, state.from, state.to);
    if (range.error) {
      problem.replaceChildren(banner(range.error));
      return;
    }
    problem.replaceChildren();
    inFlight = true;
    if (!quiet) lineHost.setAttribute("aria-busy", "true");
    try {
      const params = { from: range.from.toISOString(), ...(range.live ? {} : { to: range.to.toISOString() }) };
      const [newSummary, newSeries] = await Promise.all([
        api.get("/dashboard/summary", { ...params, category: state.category }),
        state.sensor ? api.get("/dashboard/timeseries", { ...params, sensor_id: state.sensor, interval: pickInterval(range.to - range.from) }) : null,
      ]);
      if (!alive) return;
      summary = newSummary;
      series = newSeries;
      failures = 0;
      status.textContent = `${range.live && !state.paused ? "Live" : "Updated"} · ${new Date().toLocaleTimeString()}`;
      redraw();
    } catch (err) {
      if (!alive) return;
      failures += 1;
      if (!quiet || failures >= 3) {
        problem.replaceChildren(banner(failures >= 3 ? `Connection problem: ${err.message} Still trying…` : err.message));
      }
    } finally {
      inFlight = false;
    }
  }

  function changed(key, value) {
    state[key] = value;
    customBox.hidden = state.range !== "custom";
    syncUrl();
    refresh();
  }
  sensorField.input.addEventListener("change", () => changed("sensor", sensorField.value));
  rangeField.input.addEventListener("change", () => changed("range", rangeField.value));
  categoryField.input.addEventListener("change", () => changed("category", categoryField.value));
  fromField.input.addEventListener("change", () => changed("from", fromField.value));
  toField.input.addEventListener("change", () => changed("to", toField.value));

  pauseButton.addEventListener("click", () => {
    state.paused = !state.paused;
    pauseButton.setAttribute("aria-pressed", String(state.paused));
    pauseButton.textContent = state.paused ? "Resume live updates" : "Pause live updates";
    status.textContent = state.paused ? "Paused" : "Live";
    if (!state.paused) refresh(true);
  });

  exportButton.addEventListener("click", () => {
    if (!series?.points.length) return;
    const blob = new Blob([seriesToCsv(series.points, { unit: series.unit })], { type: "text/csv;charset=utf-8" });
    saveBlob(blob, `${safeFileName(series.title)}-${state.range}.csv`);
    toast("CSV exported.", "success");
  });

  // ---------- live updates ----------
  const timer = setInterval(() => {
    const range = resolveRange(state.range, state.from, state.to);
    if (!state.paused && !document.hidden && range.live) refresh(true);
  }, POLL_MS);
  const onVisible = () => { if (!document.hidden && !state.paused) refresh(true); };
  document.addEventListener("visibilitychange", onVisible);

  // redraw charts when the width changes (rotating a phone, resizing the window)
  const observer = new ResizeObserver(() => {
    if (d3 && Math.abs(lineHost.clientWidth - lastWidth) > 1) redraw();
  });
  observer.observe(lineHost);

  loadD3().then((lib) => { d3 = lib; if (alive) redraw(); }).catch(() => {
    chartWarning.replaceChildren(banner("Charts could not be loaded (the D3 library is unavailable). The numbers and the data table still work.", "info"));
    lineHost.setAttribute("aria-busy", "false");
  });

  syncUrl();
  refresh();

  const el = h("div", {},
    pageHeader("Dashboard", status, pauseButton, exportButton),
    h("section", { class: "card controls" }, h("div", { class: "toolbar-4" }, sensorField.el, rangeField.el, categoryField.el), customBox),
    problem, chartWarning, statsHost,
    h("div", { class: "dash-grid" },
      h("section", { class: "card" }, h("h2", {}, "Readings over time"), lineHost, seriesFacts, tableHost),
      h("section", { class: "card" }, h("h2", {}, "Sensors by category"), donutHost)));

  return { el, destroy: () => { alive = false; clearInterval(timer); document.removeEventListener("visibilitychange", onVisible); observer.disconnect(); } };
}
