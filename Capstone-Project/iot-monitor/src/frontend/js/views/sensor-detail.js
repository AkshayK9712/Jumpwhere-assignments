import * as api from "../api.js";
import { emptyState, errorBox, pageHeader } from "../components.js";
import { WRITER_ROLES } from "../constants.js";
import { describeThresholds, formatDate, localInputToIso, titleCase } from "../format.js";
import * as router from "../router.js";
import { applyErrors, confirmDialog, field, h, loading, priorityBadge, setBusy, statusBadge, toast } from "../ui.js";
import { parseOptionalNumber, validateReadingForm } from "../validators.js";

export default async function sensorDetailView({ params, user }) {
  const canWrite = WRITER_ROLES.includes(user.role);
  const sensor = await api.get(`/sensors/${params.id}`);
  const meta = sensor.metadata || {};

  const detail = (label, value) => [h("dt", {}, label), h("dd", {}, value ?? "—")];
  const extras = Object.entries(meta).filter(([k]) => !["factory", "location", "unit", "thresholds"].includes(k));

  const info = h("section", { class: "card" },
    h("dl", { class: "details" },
      detail("Category", titleCase(sensor.category)),
      detail("Status", statusBadge(sensor.status)),
      detail("Priority", priorityBadge(sensor.priority)),
      detail("Factory", meta.factory),
      detail("Location", meta.location),
      detail("Unit", meta.unit),
      detail("Thresholds", describeThresholds(meta.thresholds)),
      extras.map(([k, v]) => detail(titleCase(k), typeof v === "object" ? JSON.stringify(v) : String(v))),
      detail("Created", formatDate(sensor.created_at)),
      detail("Last updated", formatDate(sensor.updated_at))),
    sensor.description ? h("p", { class: "description" }, sensor.description) : null);

  // ----- readings -----
  const readingsHost = h("div", { "aria-live": "polite" });
  async function loadReadings() {
    readingsHost.replaceChildren(loading());
    try {
      const rows = await api.get(`/sensors/${sensor.id}/readings`, { limit: 20 });
      const unit = meta.unit ? ` ${meta.unit}` : "";
      readingsHost.replaceChildren(rows.length
        ? h("div", { class: "table-wrap" }, h("table", { class: "table" },
          h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Recorded at"), h("th", { scope: "col" }, "Value"))),
          h("tbody", {}, rows.map((r) => h("tr", {}, h("td", { "data-label": "Recorded at" }, formatDate(r.recorded_at)), h("td", { "data-label": "Value" }, `${r.value}${unit}`))))))
        : emptyState("No readings yet."));
    } catch (err) {
      readingsHost.replaceChildren(errorBox(err, loadReadings));
    }
  }

  let addReading = null;
  if (canWrite) {
    const value = field({ label: "Value", name: "value", type: "number", step: "any", required: true });
    const at = field({ label: "Recorded at (optional)", name: "recorded_at", type: "datetime-local", hint: "Leave empty to use the current time." });
    const button = h("button", { type: "submit", class: "btn btn-primary" }, "Add reading");
    addReading = h("form", {
      class: "inline-form", novalidate: true,
      onsubmit: async (e) => {
        e.preventDefault();
        const errors = validateReadingForm({ value: value.value, recorded_at: at.value });
        applyErrors({ value, recorded_at: at }, errors);
        if (Object.keys(errors).length) return;
        setBusy(button, true, "Adding…");
        try {
          const body = { value: parseOptionalNumber(value.value) };
          const iso = localInputToIso(at.value);
          if (iso) body.recorded_at = iso;
          await api.post(`/sensors/${sensor.id}/readings`, body);
          value.input.value = "";
          at.input.value = "";
          toast("Reading added.", "success");
          loadReadings();
        } catch (err) {
          const rest = applyErrors({ value, recorded_at: at }, err.fieldErrors);
          if (!Object.keys(err.fieldErrors).length || rest.length) toast(err.message, "error");
        } finally {
          setBusy(button, false);
        }
      },
    }, value.el, at.el, button);
  }

  async function remove() {
    const ok = await confirmDialog({ title: "Delete sensor?", message: `“${sensor.title}” and all its readings will be permanently deleted.`, confirmText: "Delete", danger: true });
    if (!ok) return;
    try {
      await api.del(`/sensors/${sensor.id}`);
      toast("Sensor deleted.", "success");
      router.navigate("/sensors");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  loadReadings();
  return h("div", {},
    pageHeader(sensor.title,
      h("a", { class: "btn", href: "#/sensors" }, "← Back"),
      canWrite ? [h("a", { class: "btn", href: `#/sensors/${sensor.id}/edit` }, "Edit"),
        h("button", { type: "button", class: "btn btn-danger", onclick: remove }, "Delete")] : null),
    info,
    h("section", { class: "card" },
      h("div", { class: "section-head" }, h("h2", {}, "Latest readings"),
        h("button", { type: "button", class: "btn btn-sm", onclick: loadReadings }, "Refresh")),
      addReading, readingsHost));
}
