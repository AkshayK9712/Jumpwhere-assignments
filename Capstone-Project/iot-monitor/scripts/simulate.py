"""Send fake sensor readings to the API so the dashboard has live data (standard library only).

    python scripts/simulate.py                       # every 10 s, as the demo user
    python scripts/simulate.py --interval 5 --spike 0.1
    python scripts/simulate.py --base-url http://localhost:8000 --email user@example.com --password User@12345

Stop with Ctrl+C. Keep --interval at 5 or more: the default rate limit is 100 requests/minute per user.
"""
import argparse
import json
import math
import random
import time
import urllib.error
import urllib.parse
import urllib.request


class Api:
    def __init__(self, base, email, password):
        self.base, self.email, self.password, self.token = base.rstrip("/") + "/api/v1", email, password, None

    def call(self, method, path, body=None, form=None, retry=True):
        data = headers = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                return json.loads(res.read() or b"null")
        except urllib.error.HTTPError as err:
            if err.code == 401 and retry and path != "/auth/login":
                self.login()
                return self.call(method, path, body, form, retry=False)
            raise

    def login(self):
        self.token = None
        self.token = self.call("POST", "/auth/login", form={"username": self.email, "password": self.password}, retry=False)["access_token"]


def next_value(sensor, tick, rng, spike_chance):
    meta = sensor.get("metadata") or {}
    th = meta.get("thresholds") or {}
    low, high = th.get("min"), th.get("max")
    if low is not None and high is not None:
        mid, amp = (low + high) / 2, (high - low) / 6
    elif high is not None:
        mid, amp = high * 0.6, high * 0.08
    elif low is not None:
        mid, amp = low * 1.4, low * 0.08
    else:
        mid, amp = 50.0, 5.0
    value = mid + amp * math.sin(tick / 15 + sensor["id"]) + rng.uniform(-amp, amp) * 0.4
    if rng.random() < spike_chance and (high is not None or low is not None):
        value = (high * 1.08) if high is not None else low * 0.9  # a reading outside the thresholds
    return round(value, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--email", default="user@example.com")
    ap.add_argument("--password", default="User@12345")
    ap.add_argument("--interval", type=float, default=10, help="seconds between rounds (default 10)")
    ap.add_argument("--spike", type=float, default=0.03, help="chance of an out-of-threshold reading (default 0.03)")
    args = ap.parse_args()

    api, rng, tick = Api(args.base_url, args.email, args.password), random.Random(), 0
    api.login()
    print(f"Logged in as {args.email}. Sending readings every {args.interval}s. Ctrl+C to stop.")
    while True:
        sensors = api.call("GET", "/sensors?status=active&page_size=100")["items"]
        for s in sensors:
            api.call("POST", f"/sensors/{s['id']}/readings", body={"value": next_value(s, tick, rng, args.spike)})
        print(f"[{time.strftime('%H:%M:%S')}] sent {len(sensors)} readings")
        tick += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
