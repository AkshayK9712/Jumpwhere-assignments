import * as auth from "../auth.js";
import { resendBox } from "../components.js";
import { applyErrors, banner, field, h, setBusy } from "../ui.js";
import { PASSWORD_RULES, passwordProblems, validateEmail, validateName, validatePassword } from "../validators.js";

export default function registerView() {
  const name = field({ label: "Name", name: "name", required: true, autocomplete: "name", maxlength: 120 });
  const email = field({ label: "Email", name: "email", type: "email", required: true, autocomplete: "email" });
  const password = field({ label: "Password", name: "password", type: "password", required: true, autocomplete: "new-password", maxlength: 72 });
  const confirm = field({ label: "Confirm password", name: "confirm", type: "password", required: true, autocomplete: "new-password" });
  const fields = { name, email, password, confirm };

  // live checklist that mirrors the server's password rules
  const items = PASSWORD_RULES.map((rule) => ({ rule, li: h("li", {}, rule.label) }));
  const checklist = h("ul", { class: "checklist", "aria-label": "Password requirements" }, items.map((i) => i.li));
  const updateChecklist = () => {
    const unmet = passwordProblems(password.value);
    items.forEach(({ rule, li }) => li.classList.toggle("ok", !unmet.includes(rule.key)));
  };
  password.input.addEventListener("input", updateChecklist);

  const notice = h("div");
  const submit = h("button", { type: "submit", class: "btn btn-primary btn-block" }, "Create account");
  const host = h("section", { class: "card narrow" });

  const form = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      notice.replaceChildren();
      const errors = {};
      const nameError = validateName(name.value);
      const emailError = validateEmail(email.value);
      const passwordError = validatePassword(password.value);
      if (nameError) errors.name = nameError;
      if (emailError) errors.email = emailError;
      if (passwordError) errors.password = passwordError;
      if (!passwordError && password.value !== confirm.value) errors.confirm = "Passwords do not match.";
      applyErrors(fields, errors);
      if (Object.keys(errors).length) return;

      setBusy(submit, true, "Creating account…");
      try {
        await auth.register({ name: name.value.trim(), email: email.value, password: password.value });
        showSuccess(email.value.trim());
      } catch (err) {
        if (err.status === 409) email.setError("An account with this email already exists.");
        else if (err.status === 422) {
          const rest = applyErrors(fields, err.fieldErrors);
          if (rest.length) notice.replaceChildren(banner(rest.join(" ")));
        } else notice.replaceChildren(banner(err.message));
      } finally {
        setBusy(submit, false);
      }
    },
  }, name.el, email.el, password.el, checklist, confirm.el, notice, submit);

  function showSuccess(address) {
    host.replaceChildren(
      h("h1", { tabindex: "-1" }, "Check your email"),
      h("p", {}, "We sent a verification link to ", h("strong", {}, address), ". Open it to activate your account, then log in."),
      h("p", { class: "hint" }, "Running the server locally with the console email backend? The link is printed in the server terminal."),
      h("a", { class: "btn btn-primary", href: "#/login" }, "Go to log in"),
      resendBox(address),
    );
    host.querySelector("h1").focus();
  }

  host.append(h("h1", { tabindex: "-1" }, "Create your account"), form,
    h("p", { class: "muted center" }, "Already registered? ", h("a", { href: "#/login" }, "Log in")));
  return host;
}
