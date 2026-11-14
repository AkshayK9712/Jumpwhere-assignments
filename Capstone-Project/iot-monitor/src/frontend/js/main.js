import * as auth from "./auth.js";
import { markActive, renderNav } from "./nav.js";
import * as router from "./router.js";
import * as session from "./session.js";
import { toast } from "./ui.js";

import adminLogsView from "./views/admin-logs.js";
import adminUsersView from "./views/admin-users.js";
import homeView from "./views/home.js";
import loginView from "./views/login.js";
import profileView from "./views/profile.js";
import registerView from "./views/register.js";
import sensorDetailView from "./views/sensor-detail.js";
import sensorFormView from "./views/sensor-form.js";
import sensorsView from "./views/sensors.js";
import verifyView from "./views/verify.js";

// access: "public" | "guest-only" | "auth" (any logged-in user) | ["admin", ...] (specific roles)
// Order matters: "/sensors/new" must come before "/sensors/:id".
const routes = [
  { path: "/login", view: loginView, access: "guest-only" },
  { path: "/register", view: registerView, access: "guest-only" },
  { path: "/verify", view: verifyView, access: "public" },
  { path: "/", view: homeView, access: "auth" },
  { path: "/sensors", view: sensorsView, access: "auth" },
  { path: "/sensors/new", view: sensorFormView, access: ["admin", "user"] },
  { path: "/sensors/:id", view: sensorDetailView, access: "auth" },
  { path: "/sensors/:id/edit", view: sensorFormView, access: ["admin", "user"] },
  { path: "/profile", view: profileView, access: "auth" },
  { path: "/admin/users", view: adminUsersView, access: ["admin"] },
  { path: "/admin/logs", view: adminLogsView, access: ["admin"] },
];

async function boot() {
  await auth.loadCurrentUser();

  const header = document.getElementById("app-header");
  renderNav(header);
  window.addEventListener("routechange", (e) => markActive(header, e.detail.path));

  let wasLoggedIn = session.isLoggedIn();
  session.onChange(() => {
    renderNav(header);
    const now = session.isLoggedIn();
    if (wasLoggedIn && !now) {
      toast("You have been signed out.", "info");
      router.navigate("/login");
    }
    wasLoggedIn = now;
  });

  router.start(routes, document.getElementById("view"));
}

boot();
