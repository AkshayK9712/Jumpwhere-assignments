import * as auth from "../auth.js";
import { resendBox } from "../components.js";
import * as router from "../router.js";
import { banner, field, h, setBusy, toast } from "../ui.js";
import { validateEmail } from "../validators.js";

export default function loginView() {
  const email = field({ label: "Email", name: "email", type: "email", required: true, autocomplete: "username" });
  const password = field({ label: "Password", name: "password", type: "password", required: true, autocomplete: "current-password" });
  const remember = h("input", { type: "checkbox", id: "remember" });
  const notice = h("div");
  const resendHost = h("div");
  const submit = h("button", { type: "submit", class: "btn btn-primary btn-block" }, "Log in");

  const form = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      notice.replaceChildren();
      resendHost.replaceChildren();
      const emailError = validateEmail(email.value);
      const passwordError = password.value ? "" : "Password is required.";
      email.setError(emailError);
      password.setError(passwordError);
      if (emailError || passwordError) return;

      setBusy(submit, true, "Signing in…");
      try {
        const user = await auth.login(email.value, password.value, remember.checked);
        toast(`Welcome back, ${user.name}!`, "success");
        const next = router.consumeNext();
        router.navigate(next.path, next.query);
      } catch (err) {
        if (err.status === 401) notice.replaceChildren(banner("Incorrect email or password."));
        else if (err.status === 403) {
          notice.replaceChildren(banner(err.message));
          if (/not verified/i.test(err.message)) resendHost.replaceChildren(resendBox(email.value));
        } else if (err.status === 429) notice.replaceChildren(banner("Too many attempts. Please wait a minute and try again."));
        else notice.replaceChildren(banner(err.message));
      } finally {
        setBusy(submit, false);
      }
    },
  },
  email.el, password.el,
  h("label", { class: "check", for: "remember" }, remember, " Remember me on this device"),
  notice, submit);

  return h("section", { class: "card narrow" },
    h("h1", { tabindex: "-1" }, "Log in"), form, resendHost,
    h("p", { class: "muted center" }, "No account yet? ", h("a", { href: "#/register" }, "Sign up")));
}
