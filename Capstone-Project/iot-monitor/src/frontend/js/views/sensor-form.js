import * as api from "../api.js";
import { banner, pageHeader } from "../components.js";
import { CATEGORIES, PRIORITIES, STATUSES } from "../constants.js";
import { titleCase } from "../format.js";
import * as router from "../router.js";
import { applyErrors, field, h, setBusy, toast } from "../ui.js";
import { parseOptionalNumber, validateSensorForm } from "../validators.js";

const options = (list) => list.map((v) => ({ value: v, label: titleCase(v) }));
const KNOWN_META = ["factory", "location", "unit", "thresholds"];

export default async function sensorFormView({ params }) {
  const editing = Boolean(params.id);
  const sensor = editing ? await api.get(`/sensors/${params.id}`) : null;
  const meta = sensor?.metadata || {};
  // keep metadata keys this form does not edit, so saving does not delete them
  const extraMeta = Object.fromEntries(Object.entries(meta).filter(([k]) => !KNOWN_META.includes(k)));

  const fields = {
    title: field({ label: "Title", name: "title", required: true, value: sensor?.title ?? "", maxlength: 150 }),
    description: field({ label: "Description", name: "description", textarea: true, value: sensor?.description ?? "", maxlength: 1000 }),
    category: field({ label: "Category", name: "category", required: true, options: options(CATEGORIES), value: sensor?.category ?? "temperature" }),
    status: field({ label: "Status", name: "status", options: options(STATUSES), value: sensor?.status ?? "active" }),
    priority: field({ label: "Priority", name: "priority", options: options(PRIORITIES), value: sensor?.priority ?? "medium" }),
    "metadata.factory": field({ label: "Factory", name: "metadata.factory", value: meta.factory ?? "", maxlength: 100 }),
    "metadata.location": field({ label: "Location", name: "metadata.location", value: meta.location ?? "", maxlength: 100 }),
    "metadata.unit": field({ label: "Unit", name: "metadata.unit", value: meta.unit ?? "", maxlength: 20, placeholder: "°C, bar, %…" }),
    "metadata.thresholds.min": field({ label: "Minimum threshold", name: "metadata.thresholds.min", type: "number", step: "any", value: meta.thresholds?.min ?? "" }),
    "metadata.thresholds.max": field({ label: "Maximum threshold", name: "metadata.thresholds.max", type: "number", step: "any", value: meta.thresholds?.max ?? "" }),
  };
  const f = fields;
  const notice = h("div");
  const submit = h("button", { type: "submit", class: "btn btn-primary" }, editing ? "Save changes" : "Create sensor");

  function readForm() {
    return {
      title: f.title.value, description: f.description.value, category: f.category.value, status: f.status.value, priority: f.priority.value,
      factory: f["metadata.factory"].value, location: f["metadata.location"].value, unit: f["metadata.unit"].value,
      min: f["metadata.thresholds.min"].value, max: f["metadata.thresholds.max"].value,
    };
  }

  function toPayload(v) {
    const metadata = { ...extraMeta };
    for (const key of ["factory", "location", "unit"]) if (v[key].trim()) metadata[key] = v[key].trim();
    const min = parseOptionalNumber(v.min);
    const max = parseOptionalNumber(v.max);
    if (min !== null || max !== null) {
      metadata.thresholds = {};
      if (min !== null) metadata.thresholds.min = min;
      if (max !== null) metadata.thresholds.max = max;
    }
    return { title: v.title.trim(), description: v.description.trim() || null, category: v.category, status: v.status, priority: v.priority, metadata };
  }

  const form = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      notice.replaceChildren();
      const values = readForm();
      const errors = validateSensorForm(values);
      applyErrors(fields, errors);
      if (Object.keys(errors).length) return;

      setBusy(submit, true, "Saving…");
      try {
        const payload = toPayload(values);
        const saved = editing
          // If-Unmodified-Since makes the server refuse the save if someone else edited meanwhile
          ? await api.put(`/sensors/${sensor.id}`, payload, { headers: { "If-Unmodified-Since": sensor.updated_at } })
          : await api.post("/sensors", payload);
        toast(editing ? "Sensor updated." : "Sensor created.", "success");
        router.navigate(`/sensors/${saved.id}`);
      } catch (err) {
        if (err.status === 409) {
          notice.replaceChildren(banner(`${err.message}.`), h("button", { type: "button", class: "btn", onclick: () => router.navigate(`/sensors/${sensor.id}/edit`) }, "Reload latest version"));
        } else if (err.status === 422) {
          const rest = applyErrors(fields, err.fieldErrors);
          if (rest.length) notice.replaceChildren(banner(rest.join(" ")));
        } else {
          notice.replaceChildren(banner(err.message));
        }
      } finally {
        setBusy(submit, false);
      }
    },
  },
  f.title.el, f.description.el,
  h("div", { class: "grid-3" }, f.category.el, f.status.el, f.priority.el),
  h("fieldset", {}, h("legend", {}, "Where and how it measures"),
    h("div", { class: "grid-3" }, f["metadata.factory"].el, f["metadata.location"].el, f["metadata.unit"].el),
    h("div", { class: "grid-2" }, f["metadata.thresholds.min"].el, f["metadata.thresholds.max"].el)),
  notice,
  h("div", { class: "row" }, submit, h("a", { class: "btn", href: editing ? `#/sensors/${sensor.id}` : "#/sensors" }, "Cancel")));

  return h("div", {}, pageHeader(editing ? `Edit “${sensor.title}”` : "New sensor"), h("section", { class: "card" }, form));
}
