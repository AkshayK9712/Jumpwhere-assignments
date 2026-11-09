// Placeholder: the API client (token handling, retry) is built on Day 6.
async function checkHealth() {
  const el = document.getElementById("status");
  try {
    const res = await fetch("/api/v1/health");
    const data = await res.json();
    el.textContent = data.status;
  } catch (err) {
    el.textContent = "unreachable";
  }
}
checkHealth();
