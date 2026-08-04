import datetime
from decimal import Decimal

from zenml.utils.json_utils import decimal_encoder, isoformat


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


def test_decimal_encoder_whole_number() -> None:
    """A Decimal representing a whole number should encode as an int."""

    assert decimal_encoder(Decimal("5")) == 5
    assert isinstance(decimal_encoder(Decimal("5")), int)


def test_decimal_encoder_fractional_number() -> None:
    """A Decimal with a fractional part should encode as a float."""

    assert decimal_encoder(Decimal("5.25")) == 5.25
    assert isinstance(decimal_encoder(Decimal("5.25")), float)


def test_decimal_encoder_negative_whole_number() -> None:
    """A negative whole-number Decimal should still encode as an int."""

    assert decimal_encoder(Decimal("-10")) == -10
    assert isinstance(decimal_encoder(Decimal("-10")), int)


def test_decimal_encoder_zero() -> None:
    """A zero Decimal should encode as an int zero."""

    assert decimal_encoder(Decimal("0")) == 0
    assert isinstance(decimal_encoder(Decimal("0")), int)
