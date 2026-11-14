import * as auth from "../auth.js";
import { resendBox } from "../components.js";
import { h } from "../ui.js";

export default async function verifyView({ query }) {
  const card = h("section", { class: "card narrow" });
  const token = query.token;

  if (!token) {
    card.append(h("h1", { tabindex: "-1" }, "Verification link incomplete"),
      h("p", {}, "This link has no token. Open the link from your email again."), resendBox());
    return card;
  }
  try {
    await auth.verifyEmail(token);
    card.append(h("h1", { tabindex: "-1" }, "Email verified"),
      h("p", {}, "Your account is active. You can log in now."),
      h("a", { class: "btn btn-primary", href: "#/login" }, "Log in"));
  } catch (err) {
    card.append(h("h1", { tabindex: "-1" }, "Verification failed"),
      h("p", {}, err.message), h("p", { class: "hint" }, "The link may have expired. Request a new one below."), resendBox());
  }
  return card;
}
