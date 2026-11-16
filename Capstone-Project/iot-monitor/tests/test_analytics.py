from datetime import datetime, timedelta, timezone

from app.services.analytics import bucket_count, bucketize, downsample, floor_time, summarize, violation

T = datetime(2026, 11, 14, 10, 37, 45, 123456, tzinfo=timezone.utc)


def test_floor_time():
    assert floor_time(T, "minute") == datetime(2026, 11, 14, 10, 37, tzinfo=timezone.utc)
    assert floor_time(T, "hour") == datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
    assert floor_time(T, "day") == datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)


def test_floor_time_treats_naive_as_utc_and_converts_zones():
    assert floor_time(datetime(2026, 11, 14, 10, 37), "hour").tzinfo == timezone.utc
    ist = timezone(timedelta(hours=5, minutes=30))
    assert floor_time(datetime(2026, 11, 14, 3, 40, tzinfo=ist), "day") == datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def test_unknown_interval():
    try:
        floor_time(T, "week")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_bucketize_groups_and_aggregates():
    rows = [
        (T.replace(minute=5), 10.0), (T.replace(minute=20), 20.0), (T.replace(minute=59), 30.0),
        (T.replace(hour=11, minute=1), 40.0),
    ]
    points = bucketize(rows, "hour")
    assert [p["bucket"].hour for p in points] == [10, 11]
    first = points[0]
    assert (first["count"], first["min"], first["max"], first["avg"]) == (3, 10.0, 30.0, 20.0)
    assert points[1]["count"] == 1 and points[1]["avg"] == 40.0


def test_bucketize_sorts_oldest_first_even_if_input_is_not():
    rows = [(T.replace(hour=12), 1.0), (T.replace(hour=9), 2.0), (T.replace(hour=10), 3.0)]
    assert [p["bucket"].hour for p in bucketize(rows, "hour")] == [9, 10, 12]


def test_bucketize_empty():
    assert bucketize([], "hour") == []


def test_bucket_count():
    start = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
    assert bucket_count(start, start + timedelta(hours=24), "hour") == 25
    assert bucket_count(start, start + timedelta(days=365), "minute") > 2000
    assert bucket_count(start, start, "day") >= 1


def test_summarize():
    assert summarize([]) is None
    s = summarize([1.0, 5.0, 3.0])
    assert (s["count"], s["min"], s["max"], s["mean"], s["last"]) == (3, 1.0, 5.0, 3.0, 3.0)


def test_violation():
    th = {"min": 10, "max": 20}
    assert violation(5, th) == "below"
    assert violation(25, th) == "above"
    assert violation(10, th) is None and violation(20, th) is None
    assert violation(5, {"max": 20}) is None
    assert violation(99, {"min": 1}) is None
    assert violation(5, None) is None and violation(5, {}) is None


def test_downsample():
    assert downsample([1, 2, 3], 40) == [1, 2, 3]
    values = list(range(1000))
    out = downsample(values, 10)
    assert len(out) == 10 and out[0] == 0 and out[-1] == 999
