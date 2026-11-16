"""Pure functions (no database, no web) for time-series maths, so they are easy to test."""
import math
from datetime import datetime, timedelta, timezone
from typing import Iterable

INTERVALS = {
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
}


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def floor_time(dt: datetime, interval: str) -> datetime:
    """Round a timestamp down to the start of its minute / hour / day (UTC)."""
    dt = _utc(dt)
    if interval == "minute":
        return dt.replace(second=0, microsecond=0)
    if interval == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if interval == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unknown interval: {interval}")


def bucket_count(start: datetime, end: datetime, interval: str) -> int:
    """How many buckets a range can produce (upper bound)."""
    span = _utc(end) - _utc(start)
    return max(1, math.ceil(span / INTERVALS[interval]) + 1)


def bucketize(rows: Iterable[tuple[datetime, float]], interval: str) -> list[dict]:
    """Group (timestamp, value) rows into buckets with avg/min/max/count, oldest first."""
    acc: dict[datetime, list[float]] = {}  # bucket -> [count, total, min, max]
    for ts, value in rows:
        key = floor_time(ts, interval)
        slot = acc.get(key)
        if slot is None:
            acc[key] = [1, value, value, value]
        else:
            slot[0] += 1
            slot[1] += value
            slot[2] = min(slot[2], value)
            slot[3] = max(slot[3], value)
    return [
        {"bucket": key, "avg": round(total / count, 4), "min": lo, "max": hi, "count": count}
        for key, (count, total, lo, hi) in sorted(acc.items())
    ]


def summarize(values: list[float]) -> dict | None:
    if not values:
        return None
    return {"count": len(values), "min": min(values), "max": max(values), "mean": sum(values) / len(values), "last": values[-1]}


def violation(value: float, thresholds: dict | None) -> str | None:
    """'below' / 'above' when a value is outside the sensor's min/max thresholds, else None."""
    if not thresholds:
        return None
    low, high = thresholds.get("min"), thresholds.get("max")
    if low is not None and value < low:
        return "below"
    if high is not None and value > high:
        return "above"
    return None


def downsample(values: list[float], max_points: int = 40) -> list[float]:
    """Pick evenly spaced values (for small trend lines)."""
    if len(values) <= max_points or max_points < 2:
        return list(values)
    step = (len(values) - 1) / (max_points - 1)
    return [values[round(i * step)] for i in range(max_points)]
