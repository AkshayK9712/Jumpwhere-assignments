import * as auth from "./auth.js";
import * as session from "./session.js";
import { h, roleBadge } from "./ui.js";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/sensors", label: "Sensors" },
  { href: "/admin/users", label: "Users", roles: ["admin"] },
  { href: "/admin/logs", label: "Audit log", roles: ["admin"] },
];

export function renderNav(host) {
  const user = session.getUser();
  const nav = h("nav", { id: "nav", class: "nav", "aria-label": "Main" });

  if (user) {
    for (const link of LINKS) {
      if (link.roles && !link.roles.includes(user.role)) continue; // role-based menu
      nav.append(h("a", { href: `#${link.href}`, "data-path": link.href }, link.label));
    }
    nav.append(
      h("a", { href: "#/profile", "data-path": "/profile", class: "nav-user" }, user.name, " ", roleBadge(user.role)),
      h("button", { type: "button", class: "btn btn-sm", onclick: () => auth.logout() }, "Log out"),
    );
  } else {
    nav.append(
      h("a", { href: "#/login", "data-path": "/login" }, "Log in"),
      h("a", { href: "#/register", "data-path": "/register", class: "btn btn-primary btn-sm" }, "Sign up"),
    );
  }

  const toggle = h("button", {
    type: "button", class: "nav-toggle", "aria-label": "Menu", "aria-expanded": "false", "aria-controls": "nav",
    onclick: () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    },
  }, "☰");

  host.replaceChildren(h("a", { class: "brand", href: "#/" }, "IoT Monitor"), toggle, nav);
  markActive(host, currentPath());
}

function currentPath() {
  const raw = location.hash.replace(/^#/, "") || "/";
  return raw.split("?")[0] || "/";
}

export function markActive(host, path) {
  host.querySelectorAll("a[data-path]").forEach((a) => {
    const target = a.dataset.path;
    const active = target === "/" ? path === "/" : path === target || path.startsWith(`${target}/`);
    if (active) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  host.querySelector("#nav")?.classList.remove("open");
  host.querySelector(".nav-toggle")?.setAttribute("aria-expanded", "false");
}
