// Fake browser storage + a fetch mock, shared by the frontend tests.
export function fakeStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => void data.set(k, String(v)),
    removeItem: (k) => void data.delete(k),
    clear: () => data.clear(),
  };
}

export function installBrowserGlobals() {
  globalThis.localStorage = fakeStorage();
  globalThis.sessionStorage = fakeStorage();
}

export const json = (body, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

/** queue responses (or functions / errors); returns the list of calls made */
export function mockFetch(queue) {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, ...init });
    const next = queue.shift();
    if (next === undefined) throw new Error(`Unexpected fetch call: ${init.method || "GET"} ${url}`);
    if (next instanceof Error) throw next;
    return typeof next === "function" ? next(url, init) : next;
  };
  return calls;
}
