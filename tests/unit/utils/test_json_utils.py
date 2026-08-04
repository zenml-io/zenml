import datetime
from decimal import Decimal

from zenml.utils.json_utils import _json_type_of, _schema_allowed_json_types, decimal_encoder, isoformat


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


def test_json_type_of_bool_is_boolean_not_integer() -> None:
    """bool is a subclass of int in Python, so this must be checked
    before int to avoid misclassifying booleans as integers."""
    assert _json_type_of(True) == "boolean"
    assert _json_type_of(False) == "boolean"


def test_json_type_of_integer() -> None:
    """A plain int should map to the integer JSON type."""
    assert _json_type_of(42) == "integer"


def test_json_type_of_float() -> None:
    """A float should map to the number JSON type."""
    assert _json_type_of(3.14) == "number"


def test_json_type_of_string() -> None:
    """A str should map to the string JSON type."""
    assert _json_type_of("hello") == "string"


def test_json_type_of_list() -> None:
    """A list should map to the array JSON type."""
    assert _json_type_of([1, 2, 3]) == "array"


def test_json_type_of_dict() -> None:
    """A dict should map to the object JSON type."""
    assert _json_type_of({"key": "value"}) == "object"


def test_json_type_of_none() -> None:
    """None should map to the null JSON type."""
    assert _json_type_of(None) == "null"


def test_schema_allowed_json_types_single_type() -> None:
    """A schema with a single type string should return a set with
    that one type."""
    assert _schema_allowed_json_types({"type": "string"}) == {"string"}


def test_schema_allowed_json_types_list_of_types() -> None:
    """A schema with a list of types should return all of them as
    a set."""
    assert _schema_allowed_json_types(
        {"type": ["string", "null"]}
    ) == {"string", "null"}


def test_schema_allowed_json_types_missing_type_key() -> None:
    """A schema with no 'type' key should return an empty set."""
    assert _schema_allowed_json_types({}) == set()
