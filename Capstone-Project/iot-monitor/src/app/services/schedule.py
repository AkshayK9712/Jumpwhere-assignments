"""Pure helpers for scheduled reports."""
from datetime import datetime, timedelta

FREQUENCIES = {"daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}


def period(frequency: str) -> timedelta:
    try:
        return FREQUENCIES[frequency]
    except KeyError:
        raise ValueError(f"Unknown frequency: {frequency}") from None


def next_run(after: datetime, frequency: str) -> datetime:
    """Fixed periods (monthly = 30 days). A missed run is not repeated: the next one is counted from `after`."""
    return after + period(frequency)


def default_window_hours(frequency: str) -> int:
    """Each scheduled run covers one period back from the moment it runs."""
    return int(period(frequency).total_seconds() // 3600)
