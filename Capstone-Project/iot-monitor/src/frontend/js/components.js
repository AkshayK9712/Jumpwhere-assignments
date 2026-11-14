// Bigger reusable pieces built from ui.js
import * as auth from "./auth.js";
import { ApiError } from "./api.js";
import { banner, field, h, setBusy, toast } from "./ui.js";
import { validateEmail } from "./validators.js";

export function pageHeader(title, ...actions) {
  return h("div", { class: "page-header" }, h("h1", { tabindex: "-1" }, title), h("div", { class: "page-actions" }, actions));
}

export function emptyState(message, action) {
  return h("div", { class: "empty" }, h("p", {}, message), action || null);
}

/** Error box with an optional "Try again" button */
export function errorBox(err, retry) {
  const message = err instanceof ApiError ? err.message : "Something went wrong.";
  return h("div", { class: "card error-card", role: "alert" },
    h("p", {}, message),
    retry ? h("button", { type: "button", class: "btn", onclick: retry }, "Try again") : null,
  );
}

/** "Didn't get the email?" form. Always answers the same way (the server does not reveal if an account exists). */
export function resendBox(initialEmail = "") {
  const email = field({ label: "Email", name: "resend-email", type: "email", value: initialEmail, autocomplete: "email" });
  const button = h("button", { type: "submit", class: "btn" }, "Resend verification email");
  const form = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      const problem = validateEmail(email.value);
      email.setError(problem);
      if (problem) return;
      setBusy(button, true, "Sending…");
      try {
        await auth.resendVerification(email.value);
        toast("If that account needs verifying, a new email is on its way.", "success");
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setBusy(button, false);
      }
    },
  }, email.el, button);
  return h("div", { class: "resend" }, h("h2", {}, "Didn’t get the email?"), form);
}

export { banner };
