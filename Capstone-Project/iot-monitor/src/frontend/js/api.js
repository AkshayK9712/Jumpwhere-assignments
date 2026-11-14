// API client: attaches the access token, refreshes it on 401 (once, shared by parallel requests),
// retries temporary failures with back-off, and turns errors into ApiError.
import * as session from "./session.js";

export const BASE = "/api/v1";
const IDEMPOTENT = new Set(["GET", "HEAD", "PUT", "DELETE"]); // safe to repeat

const config = {
  maxRetries: 3,
  baseDelayMs: 300,
  maxRetryAfterMs: 5000,
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
};

/** For tests: configure({ sleep: async () => {} }) */
export function configure(overrides) {
  Object.assign(config, overrides);
}

export class ApiError extends Error {
  constructor(status, message, { fieldErrors = {}, body = null, retryAfter = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.body = body;
    this.retryAfter = retryAfter;
  }
}

function buildUrl(path, params) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== "") qs.append(key, String(value));
  }
  const text = qs.toString();
  return `${BASE}${path}${text ? `?${text}` : ""}`;
}

function backoff(attempt) {
  return config.baseDelayMs * 3 ** attempt; // 300ms, 900ms, 2.7s
}

function toApiError(status, body, response) {
  const detail = body && typeof body === "object" ? body.detail : null;
  const retryAfter = Number(response?.headers?.get("Retry-After")) || null;

  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{ loc: ["body","title"], msg: "..." }]
    const fieldErrors = {};
    for (const item of detail) {
      const path = (item.loc || []).filter((part) => !["body", "query", "path", "header"].includes(part)).join(".");
      const msg = String(item.msg || "Invalid value").replace(/^Value error, /, "");
      fieldErrors[path || "_"] = msg;
    }
    return new ApiError(status, "Please fix the highlighted fields.", { fieldErrors, body, retryAfter });
  }
  const message = typeof detail === "string" ? detail : `Request failed (${status})`;
  return new ApiError(status, message, { body, retryAfter });
}

async function readBody(res) {
  if (res.status === 204) return null;
  const type = res.headers.get("content-type") || "";
  try {
    return type.includes("json") ? await res.json() : await res.text();
  } catch {
    return null;
  }
}

let refreshing = null;

/** Exchange the refresh token for a new pair. Parallel callers share one request. */
function refreshTokens() {
  if (!refreshing) {
    refreshing = (async () => {
      const refreshToken = session.getRefreshToken();
      if (!refreshToken) throw new ApiError(401, "Your session has expired. Please log in again.");
      let res;
      try {
        res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
      }
      if (!res.ok) throw new ApiError(401, "Your session has expired. Please log in again.");
      session.setTokens(await res.json());
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/**
 * request("GET", "/sensors", { params, json, form, auth = true, retries, headers })
 * Resolves with the parsed body (null for 204); rejects with ApiError.
 */
export async function request(method, path, opts = {}) {
  const { params, json, form, auth = true, headers: extraHeaders = {} } = opts;
  const maxRetries = opts.retries ?? config.maxRetries;
  const idempotent = IDEMPOTENT.has(method);
  let attempt = 0;
  let refreshed = false;

  for (;;) {
    const headers = { Accept: "application/json", ...extraHeaders };
    let body;
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    } else if (form) {
      body = new URLSearchParams(form);
    }
    const token = session.getAccessToken();
    if (auth && token) headers.Authorization = `Bearer ${token}`;

    let res;
    try {
      res = await fetch(buildUrl(path, params), { method, headers, body });
    } catch {
      // network failure: only repeat requests that are safe to repeat
      if (idempotent && attempt < maxRetries) {
        await config.sleep(backoff(attempt++));
        continue;
      }
      throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
    }

    // Access token expired -> refresh once, then repeat the request
    if (res.status === 401 && auth && !refreshed && session.getRefreshToken()) {
      refreshed = true;
      try {
        await refreshTokens();
        continue;
      } catch (err) {
        if (err.status === 401) session.clearSession();
        throw err;
      }
    }

    // 429 means the server rejected it before doing anything, so any method may retry.
    // 502/503/504 are only retried for safe methods.
    const retryable = res.status === 429 || (idempotent && [502, 503, 504].includes(res.status));
    if (retryable && attempt < maxRetries) {
      const seconds = Number(res.headers.get("Retry-After"));
      const delay = seconds > 0 ? Math.min(seconds * 1000, config.maxRetryAfterMs) : backoff(attempt);
      attempt += 1;
      await config.sleep(delay);
      continue;
    }

    const data = await readBody(res);
    if (!res.ok) throw toApiError(res.status, data, res);
    return data;
  }
}

export const get = (path, params, opts) => request("GET", path, { ...opts, params });
export const post = (path, json, opts) => request("POST", path, { ...opts, json });
export const put = (path, json, opts) => request("PUT", path, { ...opts, json });
export const patch = (path, json, opts) => request("PATCH", path, { ...opts, json });
export const del = (path, opts) => request("DELETE", path, opts);
