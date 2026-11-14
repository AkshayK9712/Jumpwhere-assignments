import * as api from "../api.js";
import { pageHeader } from "../components.js";
import { WRITER_ROLES } from "../constants.js";
import { formatDate } from "../format.js";
import * as session from "../session.js";
import { applyErrors, field, h, roleBadge, setBusy, toast } from "../ui.js";
import { validateName, validateProfileForm } from "../validators.js";

export default async function profileView({ user }) {
  const canWrite = WRITER_ROLES.includes(user.role);
  const [me, profile] = await Promise.all([api.get("/users/me"), api.get("/users/me/profile")]);
  const disabled = !canWrite;

  // ----- account -----
  const name = field({ label: "Name", name: "name", value: me.name, required: true, maxlength: 120, disabled });
  const accountButton = h("button", { type: "submit", class: "btn btn-primary" }, "Save account");
  const accountForm = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      const problem = validateName(name.value);
      name.setError(problem);
      if (problem) return;
      setBusy(accountButton, true, "Saving…");
      try {
        const updated = await api.patch("/users/me", { name: name.value.trim() });
        session.setUser(updated); // refreshes the name in the menu
        name.input.value = updated.name;
        toast("Account updated.", "success");
      } catch (err) {
        if (err.fieldErrors?.name) name.setError(err.fieldErrors.name);
        else toast(err.message, "error");
      } finally {
        setBusy(accountButton, false);
      }
    },
  }, name.el, canWrite ? accountButton : null);

  // ----- profile -----
  const pf = {
    avatar_url: field({ label: "Avatar URL", name: "avatar_url", type: "url", value: profile.avatar_url ?? "", maxlength: 500, disabled, placeholder: "https://…" }),
    phone: field({ label: "Phone", name: "phone", type: "tel", value: profile.phone ?? "", maxlength: 30, disabled }),
    timezone: field({ label: "Timezone", name: "timezone", value: profile.timezone ?? "UTC", maxlength: 64, disabled, hint: "e.g. Asia/Kolkata" }),
    language: field({ label: "Language", name: "language", value: profile.language ?? "en", maxlength: 10, disabled, hint: "e.g. en or en-IN" }),
    bio: field({ label: "Bio", name: "bio", textarea: true, value: profile.bio ?? "", maxlength: 500, disabled }),
  };
  const profileButton = h("button", { type: "submit", class: "btn btn-primary" }, "Save profile");
  const profileForm = h("form", {
    class: "stack", novalidate: true,
    onsubmit: async (e) => {
      e.preventDefault();
      const values = Object.fromEntries(Object.entries(pf).map(([k, v]) => [k, v.value.trim()]));
      const errors = validateProfileForm(values);
      applyErrors(pf, errors);
      if (Object.keys(errors).length) return;
      setBusy(profileButton, true, "Saving…");
      try {
        await api.put("/users/me/profile", {
          avatar_url: values.avatar_url || null, phone: values.phone || null, bio: values.bio || null,
          timezone: values.timezone || "UTC", language: values.language || "en",
          preferences: profile.preferences || {}, // keep what we do not edit here
        });
        toast("Profile updated.", "success");
      } catch (err) {
        const rest = applyErrors(pf, err.fieldErrors || {});
        if (!Object.keys(err.fieldErrors || {}).length || rest.length) toast(err.message, "error");
      } finally {
        setBusy(profileButton, false);
      }
    },
  }, pf.avatar_url.el, h("div", { class: "grid-2" }, pf.phone.el, pf.language.el), pf.timezone.el, pf.bio.el, canWrite ? profileButton : null);

  return h("div", {},
    pageHeader("My profile"),
    !canWrite ? h("div", { class: "banner banner-info" }, "Guest accounts are read-only.") : null,
    h("section", { class: "card" },
      h("dl", { class: "details" },
        h("dt", {}, "Email"), h("dd", {}, me.email),
        h("dt", {}, "Role"), h("dd", {}, roleBadge(me.role)),
        h("dt", {}, "Last login"), h("dd", {}, formatDate(me.last_login)),
        h("dt", {}, "Member since"), h("dd", {}, formatDate(me.created_at))),
      h("h2", {}, "Account"), accountForm),
    h("section", { class: "card" }, h("h2", {}, "Profile"), profileForm));
}
