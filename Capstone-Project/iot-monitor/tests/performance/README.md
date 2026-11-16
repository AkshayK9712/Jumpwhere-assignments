# Performance tests

`load_test.py` hits the main endpoints with several concurrent virtual users and writes `results/latest.md` and `results/latest.json`.

```bash
# terminal 1: server WITHOUT rate limiting
RATE_LIMIT_ENABLED=false uvicorn app.main:app --app-dir src

# terminal 2
python tests/performance/load_test.py --users 10 --duration 20
```

Copy the generated `results/latest.md` into your submission as the "Performance Test Results".
Run it against PostgreSQL (Docker) for numbers that match production; SQLite is slower under concurrent writes.

Known limit: dashboard time series are aggregated in Python (portable across SQLite and PostgreSQL) and capped at 100,000 readings per request. For millions of readings per sensor, move the grouping into SQL (`date_trunc` on PostgreSQL) or add a rollup table.
