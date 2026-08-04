import datetime

from zenml.utils.json_utils import isoformat


def test_isoformat_date() -> None:
    """A plain date object should convert to its ISO date string."""
    assert isoformat(datetime.date(2026, 2, 18)) == "2026-02-18"


def test_isoformat_datetime() -> None:
    """A datetime object should convert to its full ISO string."""
    assert (
        isoformat(datetime.datetime(2026, 2, 18, 10, 15, 30))
        == "2026-02-18T10:15:30"
    )


def test_isoformat_time() -> None:
    """A time-only object should convert to its ISO time string."""
    assert isoformat(datetime.time(10, 15, 30)) == "10:15:30"
