// Loads D3 on demand: first from /ui/vendor/d3.min.js (offline use), then from the CDN.
const LOCAL = "vendor/d3.min.js";
const CDN = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js";
let pending = null;

function addScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => (window.d3 ? resolve() : reject(new Error(`${src} did not define d3`)));
    script.onerror = () => {
      script.remove();
      reject(new Error(`Could not load ${src}`));
    };
    document.head.append(script);
  });
}

export function loadD3() {
  if (window.d3) return Promise.resolve(window.d3);
  if (!pending) {
    pending = addScript(LOCAL)
      .catch(() => addScript(CDN))
      .then(() => window.d3)
      .catch((err) => {
        pending = null; // allow another attempt later
        throw err;
      });
  }
  return pending;
}
