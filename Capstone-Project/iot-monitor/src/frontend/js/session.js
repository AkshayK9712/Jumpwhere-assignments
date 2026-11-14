// Token storage. "Remember me" -> localStorage (survives closing the browser);
// otherwise sessionStorage (cleared when the tab closes).
const KEY = "iot.session";
const listeners = new Set();

function stores() {
  try {
    return [localStorage, sessionStorage];
  } catch {
    return [];
  }
}

function read() {
  for (const store of stores()) {
    try {
      const raw = store.getItem(KEY);
      if (raw) return JSON.parse(raw);
    } catch {
      /* ignore corrupt data */
    }
  }
  return null;
}

let tokens = read(); // { access_token, refresh_token, remember }
let user = null;

function emit() {
  listeners.forEach((fn) => fn());
}

export function onChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setTokens(newTokens, remember = tokens?.remember ?? false) {
  tokens = { access_token: newTokens.access_token, refresh_token: newTokens.refresh_token, remember };
  const [keep, drop] = remember ? stores() : stores().reverse();
  try {
    keep?.setItem(KEY, JSON.stringify(tokens));
    drop?.removeItem(KEY);
  } catch {
    /* storage may be blocked; the session then lasts until reload */
  }
  emit();
}

export function clearSession() {
  tokens = null;
  user = null;
  for (const store of stores()) {
    try {
      store.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }
  emit();
}

export const getAccessToken = () => tokens?.access_token ?? null;
export const getRefreshToken = () => tokens?.refresh_token ?? null;
export const isLoggedIn = () => Boolean(tokens?.access_token);
export const getUser = () => user;

export function setUser(newUser) {
  user = newUser;
  emit();
}

export function hasRole(...roles) {
  return Boolean(user && roles.includes(user.role));
}
