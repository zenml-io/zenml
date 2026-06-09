import datetime as dt

import pytest

from zenml.utils import native_schedules


def _freeze_now(monkeypatch: pytest.MonkeyPatch, frozen: dt.datetime) -> None:
    """Patch the module-local datetime.now() used in native_schedules."""

    class FrozenDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen.replace(tzinfo=None)
            if frozen.tzinfo is None:
                return frozen.replace(tzinfo=tz)
            return frozen.astimezone(tz)

    monkeypatch.setattr(native_schedules, "datetime", FrozenDateTime)


def _assert_naive(value: dt.datetime) -> None:
    assert isinstance(value, dt.datetime)
    assert value.tzinfo is None


def test_next_occurrence_for_interval_standard_scenarios() -> None:
    """Covers common interval scheduling scenarios."""
    cases = [
        {
            "name": "base between two occurrences",
            "interval": 300,
            "start": dt.datetime(2026, 1, 1, 10, 0, 0),
            "base": dt.datetime(2026, 1, 1, 10, 7, 30),
            "expected": dt.datetime(2026, 1, 1, 10, 10, 0),
        },
        {
            "name": "base exactly on an occurrence returns next one",
            "interval": 300,
            "start": dt.datetime(2026, 1, 1, 10, 0, 0),
            "base": dt.datetime(2026, 1, 1, 10, 10, 0),
            "expected": dt.datetime(2026, 1, 1, 10, 15, 0),
        },
        {
            "name": "base before start returns start",
            "interval": 300,
            "start": dt.datetime(2026, 1, 1, 10, 0, 0),
            "base": dt.datetime(2026, 1, 1, 9, 58, 0),
            "expected": dt.datetime(2026, 1, 1, 10, 0, 0),
        },
    ]

    for case in cases:
        result = native_schedules.next_occurrence_for_interval(
            interval=case["interval"],
            start=case["start"],
            base=case["base"],
        )

        assert result == case["expected"], case["name"]
        _assert_naive(result)


def test_next_occurrence_for_cron_standard_scenarios() -> None:
    """Covers common cron scheduling scenarios."""
    cases = [
        {
            "name": "every 15 minutes",
            "expression": "*/15 * * * *",
            "base": dt.datetime(2026, 1, 1, 10, 7, 0),
            "expected": dt.datetime(2026, 1, 1, 10, 15, 0),
        },
        {
            "name": "top of next hour",
            "expression": "0 * * * *",
            "base": dt.datetime(2026, 1, 1, 10, 7, 0),
            "expected": dt.datetime(2026, 1, 1, 11, 0, 0),
        },
        {
            "name": "daily midnight rollover",
            "expression": "0 0 * * *",
            "base": dt.datetime(2026, 1, 1, 23, 59, 59),
            "expected": dt.datetime(2026, 1, 2, 0, 0, 0),
        },
    ]

    for case in cases:
        result = native_schedules.next_occurrence_for_cron(
            expression=case["expression"],
            base=case["base"],
        )

        assert isinstance(result, dt.datetime), case["name"]
        assert result == case["expected"], case["name"]
        _assert_naive(result)


def test_calculate_first_occurrence_standard_scenarios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers the standard branches of calculate_first_occurrence."""
    frozen_now = dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    cases = [
        {
            "name": "cron with past start_time uses now + 1 second",
            "kwargs": {
                "cron_expression": "*/5 * * * *",
                "start_time": dt.datetime(2026, 1, 1, 9, 0, 0),
            },
            "expected": dt.datetime(2026, 1, 1, 10, 5, 0),
        },
        {
            "name": "cron with future start_time uses start_time as base",
            "kwargs": {
                "cron_expression": "0 * * * *",
                "start_time": dt.datetime(2026, 1, 1, 10, 30, 0),
            },
            "expected": dt.datetime(2026, 1, 1, 11, 0, 0),
        },
        {
            "name": "interval with past start_time computes next occurrence",
            "kwargs": {
                "interval": 300,
                "start_time": dt.datetime(2026, 1, 1, 9, 58, 0),
            },
            "expected": dt.datetime(2026, 1, 1, 10, 3, 0),
        },
        {
            "name": "run once returns provided datetime",
            "kwargs": {
                "run_once_start_time": dt.datetime(2026, 1, 1, 12, 0, 0),
            },
            "expected": dt.datetime(2026, 1, 1, 12, 0, 0),
        },
        {
            "name": "no scheduling information returns None",
            "kwargs": {},
            "expected": None,
        },
    ]

    for case in cases:
        result = native_schedules.calculate_first_occurrence(**case["kwargs"])
        assert result == case["expected"], case["name"]
        if result is not None:
            _assert_naive(result)


def test_timezone_agnostic_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures all returned datetimes are timezone agnostic, including edge cases."""
    frozen_now = dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc)
    _freeze_now(monkeypatch, frozen_now)

    cases = [
        {
            "name": "next_occurrence_for_interval with aware inputs",
            "call": lambda: native_schedules.next_occurrence_for_interval(
                interval=300,
                start=dt.datetime(
                    2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc
                ),
                base=dt.datetime(2026, 1, 1, 10, 7, 0, tzinfo=dt.timezone.utc),
            ),
        },
        {
            "name": "next_occurrence_for_cron with aware base",
            "call": lambda: native_schedules.next_occurrence_for_cron(
                expression="0 * * * *",
                base=dt.datetime(2026, 1, 1, 10, 7, 0, tzinfo=dt.timezone.utc),
            ),
        },
        {
            "name": "calculate_first_occurrence interval future aware start_time",
            "call": lambda: native_schedules.calculate_first_occurrence(
                interval=300,
                start_time=dt.datetime(
                    2026, 1, 1, 10, 30, 0, tzinfo=dt.timezone.utc
                ),
            ),
        },
        {
            "name": "calculate_first_occurrence run_once aware start_time",
            "call": lambda: native_schedules.calculate_first_occurrence(
                run_once_start_time=dt.datetime(
                    2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc
                ),
            ),
        },
    ]

    for case in cases:
        result = case["call"]()
        assert result is not None, case["name"]
        assert result.tzinfo is None, case["name"]
