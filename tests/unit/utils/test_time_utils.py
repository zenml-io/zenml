from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from zenml.utils.time_utils import exponential_backoff_delays, expires_in, iso8601_to_utc_naive, seconds_to_human_readable, to_local_tz, to_utc_timezone, utc_now, utc_now_tz_aware


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


def test_seconds_to_human_readable_simple_minutes() -> None:
    """90 seconds should read as 1 minute 30 seconds."""
    assert seconds_to_human_readable(90) == "1m30s"


def test_seconds_to_human_readable_all_units() -> None:
    """A value spanning days, hours, minutes and seconds."""
    total = 86400 + 7200 + 180 + 4
    assert seconds_to_human_readable(total) == "1d2h3m4s"


def test_seconds_to_human_readable_zero() -> None:
    """Zero seconds should return an empty string, since no token applies."""
    assert seconds_to_human_readable(0) == ""


def test_seconds_to_human_readable_exact_minute() -> None:
    """Exactly 60 seconds should roll over to 1 minute, not '60s'."""
    assert seconds_to_human_readable(60) == "1m"


def test_expires_in_future() -> None:
    """When expiry is in the future, returns human-readable time left."""
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    future_time = fixed_now + timedelta(seconds=90)
    with patch("zenml.utils.time_utils.utc_now", return_value=fixed_now):
        result = expires_in(future_time, "expired")
    assert result == "1m30s"


def test_expires_in_expired() -> None:
    """When expiry is in the past, returns the expired string."""
    past_time = datetime.now(timezone.utc) - timedelta(seconds=90)
    result = expires_in(past_time, "expired")
    assert result == "expired"


def test_expires_in_skew_tolerance() -> None:
    """When skew_tolerance pushes an otherwise-future expiry into the past,
    returns the expired string."""
    near_future = datetime.now(timezone.utc) + timedelta(seconds=60)
    result = expires_in(near_future, "expired", skew_tolerance=120)
    assert result == "expired"


def test_expires_in_boundary_now() -> None:
    """When expiry is exactly now, treated as expired."""
    now_time = datetime.now(timezone.utc)
    result = expires_in(now_time, "expired")
    assert result == "expired"


def test_to_utc_timezone_naive_input() -> None:
    """A naive datetime is assumed to already be UTC and gets tagged as such."""
    naive_dt = datetime(2026, 1, 1, 10, 0, 0)
    result = to_utc_timezone(naive_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc


def test_to_utc_timezone_already_utc() -> None:
    """A datetime already in UTC should be returned unchanged in value."""
    utc_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    result = to_utc_timezone(utc_dt)
    assert result == utc_dt
    assert result.tzinfo == timezone.utc


def test_to_utc_timezone_converts_other_timezone() -> None:
    """A datetime in IST (+5:30) should be converted to the correct UTC time."""
    ist = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime(2026, 1, 1, 15, 30, 0, tzinfo=ist)
    result = to_utc_timezone(ist_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_to_utc_timezone_negative_offset() -> None:
    """A datetime in a negative-offset timezone (e.g. US Eastern, -5:00) converts correctly."""
    est = timezone(timedelta(hours=-5))
    est_dt = datetime(2026, 1, 1, 5, 0, 0, tzinfo=est)
    result = to_utc_timezone(est_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_to_local_tz_naive_input() -> None:
    """A naive datetime is assumed UTC, then converted to local time."""
    naive_dt = datetime(2026, 1, 1, 10, 0, 0)
    result = to_local_tz(naive_dt)
    expected = naive_dt.replace(tzinfo=timezone.utc).astimezone()
    assert result == expected
    assert result.tzinfo is not None


def test_to_local_tz_already_utc() -> None:
    """A UTC-aware datetime converts to the local equivalent instant."""
    utc_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    result = to_local_tz(utc_dt)
    assert result == utc_dt.astimezone()
    assert result.astimezone(timezone.utc) == utc_dt


def test_to_local_tz_from_other_timezone() -> None:
    """A datetime in another timezone (IST) still lands on the correct instant locally."""
    ist = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime(2026, 1, 1, 15, 30, 0, tzinfo=ist)
    result = to_local_tz(ist_dt)
    assert result == ist_dt.astimezone()
    assert result.astimezone(timezone.utc) == ist_dt.astimezone(timezone.utc)


def test_to_local_tz_preserves_instant() -> None:
    """Converting to local tz must never change the actual point in time, only its label."""
    dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = to_local_tz(dt)
    assert result.astimezone(timezone.utc) == dt


def test_utc_now_default_naive() -> None:
    """Default call (tz_aware=False) returns a naive datetime close to now."""
    result = utc_now()
    assert result.tzinfo is None
    real_now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((real_now - result).total_seconds()) < 2


def test_utc_now_tz_aware_true() -> None:
    """tz_aware=True returns a UTC-aware datetime."""
    result = utc_now(tz_aware=True)
    assert result.tzinfo == timezone.utc


def test_utc_now_matches_naive_reference() -> None:
    """Passing a naive datetime as tz_aware makes the result naive too."""
    naive_ref = datetime(2020, 1, 1)
    result = utc_now(tz_aware=naive_ref)
    assert result.tzinfo is None


def test_utc_now_matches_aware_reference() -> None:
    """Passing a tz-aware datetime as tz_aware makes the result aware too."""
    aware_ref = datetime(2020, 1, 1, tzinfo=timezone.utc)
    result = utc_now(tz_aware=aware_ref)
    assert result.tzinfo == timezone.utc


def test_utc_now_tz_aware_wrapper() -> None:
    """utc_now_tz_aware() always returns a UTC-aware datetime."""
    result = utc_now_tz_aware()
    assert result.tzinfo == timezone.utc


def test_exponential_backoff_no_jitter_basic_sequence() -> None:
    """With jitter='none', delays double each time up to max_delay."""
    delays = list(
        exponential_backoff_delays(
            attempts=5, initial_delay=1.0, max_delay=30.0, factor=2.0, jitter="none"
        )
    )
    assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_exponential_backoff_respects_max_delay() -> None:
    """Delays are capped at max_delay once the exponential growth exceeds it."""
    delays = list(
        exponential_backoff_delays(
            attempts=6, initial_delay=1.0, max_delay=10.0, factor=2.0, jitter="none"
        )
    )
    assert delays == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]


def test_exponential_backoff_zero_attempts_yields_nothing() -> None:
    """attempts=0 should yield no delays at all."""
    delays = list(exponential_backoff_delays(attempts=0, jitter="none"))
    assert delays == []


def test_exponential_backoff_full_jitter_within_bounds() -> None:
    """jitter='full' should keep every delay between 0 and the computed max for that step."""
    delays = list(
        exponential_backoff_delays(
            attempts=5, initial_delay=1.0, max_delay=30.0, factor=2.0, jitter="full"
        )
    )
    expected_caps = [1.0, 2.0, 4.0, 8.0, 16.0]
    for delay, cap in zip(delays, expected_caps):
        assert 0 <= delay <= cap


def test_exponential_backoff_equal_jitter_within_bounds() -> None:
    """jitter='equal' should keep delays between half and the full computed delay."""
    delays = list(
        exponential_backoff_delays(
            attempts=5, initial_delay=1.0, max_delay=30.0, factor=2.0, jitter="equal"
        )
    )
    expected_caps = [1.0, 2.0, 4.0, 8.0, 16.0]
    for delay, cap in zip(delays, expected_caps):
        assert cap / 2 <= delay <= cap


def test_exponential_backoff_negative_attempts_raises() -> None:
    """A negative attempts count is invalid."""
    with pytest.raises(ValueError):
        list(exponential_backoff_delays(attempts=-1))


def test_exponential_backoff_zero_initial_delay_raises() -> None:
    """initial_delay must be greater than 0."""
    with pytest.raises(ValueError):
        list(exponential_backoff_delays(attempts=3, initial_delay=0))


def test_exponential_backoff_zero_max_delay_raises() -> None:
    """max_delay must be greater than 0."""
    with pytest.raises(ValueError):
        list(exponential_backoff_delays(attempts=3, max_delay=0))


def test_exponential_backoff_factor_below_one_raises() -> None:
    """factor must be at least 1."""
    with pytest.raises(ValueError):
        list(exponential_backoff_delays(attempts=3, factor=0.5))


def test_exponential_backoff_invalid_jitter_raises() -> None:
    """jitter must be one of 'none', 'full', or 'equal'."""
    with pytest.raises(ValueError):
        list(exponential_backoff_delays(attempts=3, jitter="bogus"))
