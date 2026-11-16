"""Simple load test (standard library only).

1. Start the API with rate limiting OFF, otherwise you will mostly measure 429 responses:
       RATE_LIMIT_ENABLED=false uvicorn app.main:app --app-dir src          (PowerShell: $env:RATE_LIMIT_ENABLED="false")
2. Run:
       python tests/performance/load_test.py --users 10 --duration 20
3. Results are printed and written to tests/performance/results/latest.md and latest.json

Targets (see docs/srs.json): p95 latency under 300 ms for read endpoints, error rate under 1 %.
"""
import argparse
import json
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

P95_TARGET_MS = 300
ERROR_TARGET = 0.01


def call(base, method, path, token=None, form=None, body=None):
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
    elif body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = res.read()
            status = res.status
    except urllib.error.HTTPError as err:
        payload, status = err.read(), err.code
    except Exception:
        payload, status = b"", 0
    return status, (time.perf_counter() - start) * 1000, payload


def percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--email", default="user@example.com")
    ap.add_argument("--password", default="User@12345")
    ap.add_argument("--users", type=int, default=10, help="concurrent virtual users (threads)")
    ap.add_argument("--duration", type=int, default=20, help="seconds")
    args = ap.parse_args()
    base = args.base_url.rstrip("/") + "/api/v1"

    status, _, payload = call(base, "POST", "/auth/login", form={"username": args.email, "password": args.password})
    if status != 200:
        raise SystemExit(f"Login failed ({status}). Is the server running and seeded?")
    token = json.loads(payload)["access_token"]
    sensors = json.loads(call(base, "GET", "/sensors?page_size=100", token)[2])["items"]
    if not sensors:
        raise SystemExit("No sensors found. Run: python scripts/seed.py")
    sid = sensors[0]["id"]

    scenarios = [
        ("GET /health", "GET", "/health", False),
        ("GET /sensors", "GET", "/sensors?page_size=20", True),
        ("GET /sensors?q=&sort", "GET", "/sensors?q=temp&sort=-priority", True),
        ("GET /sensors/{id}", "GET", f"/sensors/{sid}", True),
        ("GET /sensors/{id}/readings", "GET", f"/sensors/{sid}/readings?limit=100", True),
        ("GET /dashboard/summary", "GET", "/dashboard/summary", True),
        ("GET /dashboard/timeseries", "GET", f"/dashboard/timeseries?sensor_id={sid}&interval=hour", True),
        ("POST /sensors/{id}/readings", "POST", f"/sensors/{sid}/readings", True),
    ]
    samples = {name: [] for name, *_ in scenarios}
    codes = {name: {} for name, *_ in scenarios}
    lock, stop = threading.Lock(), time.time() + args.duration

    def worker(offset):
        i = offset
        while time.time() < stop:
            name, method, path, auth = scenarios[i % len(scenarios)]
            i += 1
            body = {"value": 20 + (i % 10)} if method == "POST" else None
            status, ms, _ = call(base, method, path, token if auth else None, body=body)
            with lock:
                samples[name].append(ms)
                codes[name][status] = codes[name].get(status, 0) + 1

    started = time.time()
    threads = [threading.Thread(target=worker, args=(n,)) for n in range(args.users)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    elapsed = time.time() - started

    rows, total, failed, all_ms, rate_limited = [], 0, 0, [], 0
    for name, *_ in scenarios:
        ms = samples[name]
        bad = sum(n for s, n in codes[name].items() if s == 0 or s >= 400)
        rate_limited += codes[name].get(429, 0)
        total, failed, all_ms = total + len(ms), failed + bad, all_ms + ms
        rows.append({"endpoint": name, "requests": len(ms), "errors": bad, "p50_ms": round(percentile(ms, 50), 1),
                     "p95_ms": round(percentile(ms, 95), 1), "p99_ms": round(percentile(ms, 99), 1),
                     "mean_ms": round(statistics.fmean(ms), 1) if ms else 0, "max_ms": round(max(ms), 1) if ms else 0})

    overall = {"requests": total, "errors": failed, "error_rate": round(failed / total, 4) if total else 0,
               "rps": round(total / elapsed, 1), "p95_ms": round(percentile(all_ms, 95), 1), "p99_ms": round(percentile(all_ms, 99), 1)}
    reads = [r for r in rows if r["endpoint"].startswith("GET")]
    slow = [r["endpoint"] for r in reads if r["p95_ms"] > P95_TARGET_MS]
    passed = not slow and overall["error_rate"] <= ERROR_TARGET
    result = {"when_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "users": args.users, "duration_s": round(elapsed, 1),
              "sensors_in_database": len(sensors), "overall": overall, "endpoints": rows, "passed": passed,
              "targets": {"read_p95_ms": P95_TARGET_MS, "max_error_rate": ERROR_TARGET}}

    lines = [f"# Performance test results", "",
             f"- Run at: {result['when_utc']} UTC", f"- Virtual users: {args.users}, duration: {result['duration_s']} s",
             f"- Throughput: **{overall['rps']} requests/s** ({total} requests, {failed} errors, error rate {overall['error_rate']:.2%})",
             f"- Overall p95: {overall['p95_ms']} ms, p99: {overall['p99_ms']} ms",
             f"- Target: read endpoints p95 under {P95_TARGET_MS} ms and error rate under {ERROR_TARGET:.0%}: **{'PASS' if passed else 'FAIL'}**", "",
             "| Endpoint | Requests | Errors | p50 ms | p95 ms | p99 ms | mean ms | max ms |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['endpoint']} | {r['requests']} | {r['errors']} | {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['mean_ms']} | {r['max_ms']} |" for r in rows]
    if rate_limited:
        lines += ["", f"> **Warning:** {rate_limited} responses were 429 (rate limited). Restart the server with RATE_LIMIT_ENABLED=false for a meaningful test."]
    if slow:
        lines += ["", f"> Endpoints over the p95 target: {', '.join(slow)}"]

    out = Path(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)
    (out / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "latest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to {out / 'latest.md'}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
