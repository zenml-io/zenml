"""Tests for time utilities."""

from datetime import datetime

import pytest

from zenml.utils.time_utils import (
    exponential_backoff_delays,
    iso8601_to_utc_naive,
)


def test_exponential_backoff_remains_capped_for_many_attempts() -> None:
    """Ensure capped backoff delays do not overflow after many attempts."""
    delays = list(
        exponential_backoff_delays(
            attempts=2000,
            initial_delay=1.0,
            max_delay=20.0,
            factor=2.0,
            jitter="none",
        )
    )

    assert delays[:6] == [1.0, 2.0, 4.0, 8.0, 16.0, 20.0]
    assert delays[-1] == 20.0


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
