from datetime import datetime, timezone

import pytest

from zenml.utils.time_utils import (
    from_unix_nanos,
    iso8601_to_utc_naive,
    to_unix_nanos,
)


def test_iso8601_to_utc_naive_expected_behaviors() -> None:
    """Covers expected parsing and UTC-normalization behavior."""
    # Offset -> converted to UTC, returned naive
    assert iso8601_to_utc_naive("2026-02-18T10:15:30+02:00") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Zulu -> treated as UTC, returned naive
    assert iso8601_to_utc_naive("2026-02-18T08:15:30Z") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Naive -> returned as-is
    assert iso8601_to_utc_naive("2026-02-18T08:15:30") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Whitespace tolerated
    assert iso8601_to_utc_naive(" 2026-02-18T08:15:30Z  ") == datetime(
        2026, 2, 18, 8, 15, 30
    )


def test_iso8601_to_utc_naive_unexpected_inputs_raise_value_error() -> None:
    """Covers invalid inputs that must raise ValueError."""
    with pytest.raises(ValueError):
        iso8601_to_utc_naive("")

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("not-a-date")

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("2026-02-30T08:15:30")  # invalid date

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("2026-02-18T08:15:30+99:99")  # invalid offset


def test_unix_nanos_keeps_every_microsecond_of_a_modern_date() -> None:
    """The float a datetime reports cannot hold nanoseconds of a modern date."""
    moment = datetime(2026, 2, 18, 8, 15, 30, 123456, tzinfo=timezone.utc)

    nanos = to_unix_nanos(moment)

    assert nanos % 1_000_000_000 == 123_456_000
    assert from_unix_nanos(nanos) == moment


def test_unix_nanos_assumes_utc_for_a_naive_datetime() -> None:
    """Covers the timezone handling shared with the rest of these helpers."""
    naive = datetime(2026, 2, 18, 8, 15, 30)

    assert to_unix_nanos(naive) == to_unix_nanos(
        naive.replace(tzinfo=timezone.utc)
    )


def test_unix_nanos_truncates_below_a_microsecond() -> None:
    """A datetime has no room for the finer detail a log backend may report."""
    assert from_unix_nanos(1_786_983_319_196_431_104) == datetime(
        2026, 8, 17, 16, 15, 19, 196431, tzinfo=timezone.utc
    )
