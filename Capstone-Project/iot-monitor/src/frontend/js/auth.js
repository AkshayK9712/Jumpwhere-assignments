import * as api from "./api.js";
import * as session from "./session.js";

export async function login(email, password, remember) {
  const tokens = await api.request("POST", "/auth/login", {
    form: { username: email.trim(), password, remember_me: String(Boolean(remember)) },
    auth: false,
    retries: 0, // never auto-repeat a login
  });
  session.setTokens(tokens, Boolean(remember));
  try {
    const user = await api.get("/users/me");
    session.setUser(user);
    return user;
  } catch (err) {
    session.clearSession();
    throw err;
  }
}

export const register = ({ name, email, password }) =>
  api.post("/auth/register", { name, email: email.trim(), password }, { auth: false, retries: 0 });

export const resendVerification = (email) =>
  api.post("/auth/resend-verification", { email: email.trim() }, { auth: false, retries: 0 });

export const verifyEmail = (token) => api.get("/auth/verify-email", { token }, { auth: false });

export async function logout() {
  const refreshToken = session.getRefreshToken();
  try {
    if (refreshToken) await api.post("/auth/logout", { refresh_token: refreshToken }, { retries: 0 });
  } catch {
    /* even if the server call fails we still sign out locally */
  }
  session.clearSession();
}

/** Called once at startup: restore the user if a saved session exists. */
export async function loadCurrentUser() {
  if (!session.isLoggedIn()) return null;
  try {
    const user = await api.get("/users/me");
    session.setUser(user);
    return user;
  } catch (err) {
    if (err.status === 401 || err.status === 403) session.clearSession();
    return null;
  }
}
