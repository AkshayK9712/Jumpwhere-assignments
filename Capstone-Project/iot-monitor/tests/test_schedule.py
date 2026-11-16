from datetime import datetime, timedelta, timezone

from app.services.schedule import default_window_hours, next_run, period

NOW = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)


def test_periods():
    assert period("daily") == timedelta(days=1)
    assert period("weekly") == timedelta(days=7)
    assert period("monthly") == timedelta(days=30)


def test_next_run_counts_from_the_given_time():
    assert next_run(NOW, "daily") == NOW + timedelta(days=1)
    assert next_run(NOW, "weekly") == NOW + timedelta(days=7)


def test_window_hours_match_the_frequency():
    assert default_window_hours("daily") == 24
    assert default_window_hours("weekly") == 168
    assert default_window_hours("monthly") == 720


def test_unknown_frequency():
    try:
        period("hourly")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
