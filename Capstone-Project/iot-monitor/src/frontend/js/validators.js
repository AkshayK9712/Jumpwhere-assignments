// Client-side validation (CRUD-002). The server validates again; this only gives faster feedback.
import { CATEGORIES, PRIORITIES, STATUSES } from "./constants.js";

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(value) {
  const v = (value || "").trim();
  if (!v) return "Email is required.";
  if (!EMAIL_RE.test(v)) return "Enter a valid email address.";
  return "";
}

/** Same rules (and wording keys) as the server: see app/core/security.py */
export const PASSWORD_RULES = [
  { key: "at least 8 characters", label: "At least 8 characters", test: (p) => p.length >= 8 },
  { key: "an uppercase letter", label: "An uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { key: "a lowercase letter", label: "A lowercase letter", test: (p) => /[a-z]/.test(p) },
  { key: "a digit", label: "A digit", test: (p) => /\d/.test(p) },
  { key: "a symbol", label: "A symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export function passwordProblems(password) {
  return PASSWORD_RULES.filter((r) => !r.test(password || "")).map((r) => r.key);
}

export function validatePassword(password) {
  if (!password) return "Password is required.";
  if (password.length > 72) return "Password must be 72 characters or fewer.";
  const problems = passwordProblems(password);
  return problems.length ? `Password needs ${problems.join(", ")}.` : "";
}

export function validateName(value) {
  const v = (value || "").trim();
  if (!v) return "Name is required.";
  if (v.length > 120) return "Name must be 120 characters or fewer.";
  return "";
}

/** "" -> null (not given), "abc" -> NaN (invalid), "12.5" -> 12.5 */
export function parseOptionalNumber(text) {
  const t = String(text ?? "").trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : NaN;
}

export function validateSensorForm(v) {
  const errors = {};
  const title = (v.title || "").trim();
  if (!title) errors.title = "Title is required.";
  else if (title.length > 150) errors.title = "Title must be 150 characters or fewer.";

  if ((v.description || "").length > 1000) errors.description = "Description must be 1000 characters or fewer.";
  if (!CATEGORIES.includes(v.category)) errors.category = "Choose a category.";
  if (!STATUSES.includes(v.status)) errors.status = "Choose a status.";
  if (!PRIORITIES.includes(v.priority)) errors.priority = "Choose a priority.";

  for (const [key, max] of [["factory", 100], ["location", 100], ["unit", 20]]) {
    if ((v[key] || "").length > max) errors[`metadata.${key}`] = `Must be ${max} characters or fewer.`;
  }

  const min = parseOptionalNumber(v.min);
  const max = parseOptionalNumber(v.max);
  if (Number.isNaN(min)) errors["metadata.thresholds.min"] = "Enter a number.";
  if (Number.isNaN(max)) errors["metadata.thresholds.max"] = "Enter a number.";
  if (min !== null && max !== null && !Number.isNaN(min) && !Number.isNaN(max) && min > max) {
    errors["metadata.thresholds.max"] = "Max must be greater than or equal to min.";
  }
  return errors;
}

export function validateReadingForm(v, now = new Date()) {
  const errors = {};
  const value = parseOptionalNumber(v.value);
  if (value === null) errors.value = "Value is required.";
  else if (Number.isNaN(value)) errors.value = "Enter a number.";
  if (v.recorded_at) {
    const d = new Date(v.recorded_at);
    if (Number.isNaN(d.getTime())) errors.recorded_at = "Enter a valid date and time.";
    else if (d.getTime() > now.getTime() + 5 * 60 * 1000) errors.recorded_at = "Time cannot be in the future.";
  }
  return errors;
}

export function validateProfileForm(v) {
  const errors = {};
  if (v.avatar_url && !/^https?:\/\//i.test(v.avatar_url)) errors.avatar_url = "Must start with http:// or https://";
  if ((v.bio || "").length > 500) errors.bio = "Bio must be 500 characters or fewer.";
  if (v.phone && !/^[0-9+()\-\s]{5,30}$/.test(v.phone)) errors.phone = "Use digits, spaces, + - ( ) only (5-30 characters).";
  if (v.timezone && !/^[A-Za-z0-9_+\-/]{1,64}$/.test(v.timezone)) errors.timezone = "Invalid timezone name.";
  if (v.language && !/^[a-z]{2,3}(-[A-Za-z]{2,4})?$/.test(v.language)) errors.language = "Use a code like en or en-US.";
  return errors;
}
