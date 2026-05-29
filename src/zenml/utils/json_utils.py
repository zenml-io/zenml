#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""JSON helpers, including pydantic v1 encoders and schema-aware parsing.

Check out the latest version of the pydantic helpers here:
https://github.com/pydantic/pydantic/blob/v1.10.15/pydantic/json.py
"""

import datetime
import json
from collections import deque
from decimal import Decimal
from enum import Enum
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import Path
from re import Pattern
from types import GeneratorType
from typing import Any, Callable, Dict, Optional, Set, Type, Union
from uuid import UUID

from pydantic import NameEmail, SecretBytes, SecretStr
from pydantic.color import Color

__all__ = ["parse_value_for_schema", "pydantic_encoder"]


def isoformat(obj: Union[datetime.date, datetime.time]) -> str:
    """Function to convert a datetime into iso format.

    Args:
        obj: input datetime

    Returns:
        the corresponding time in iso format.
    """
    return obj.isoformat()


def decimal_encoder(dec_value: Decimal) -> Union[int, float]:
    """Encodes a Decimal as int of there's no exponent, otherwise float.

    This is useful when we use ConstrainedDecimal to represent Numeric(x,0)
    where an integer (but not int typed) is used. Encoding this as a float
    results in failed round-tripping between encode and parse.
    Our ID type is a prime example of this.

    >>> decimal_encoder(Decimal("1.0"))
    1.0

    >>> decimal_encoder(Decimal("1"))
    1

    Args:
        dec_value: The input Decimal value

    Returns:
        the encoded result
    """
    if dec_value.as_tuple().exponent >= 0:  # type: ignore[operator]
        return int(dec_value)
    else:
        return float(dec_value)


ENCODERS_BY_TYPE: Dict[Type[Any], Callable[[Any], Any]] = {
    bytes: lambda obj: obj.decode(),
    Color: str,
    datetime.date: isoformat,
    datetime.datetime: isoformat,
    datetime.time: isoformat,
    datetime.timedelta: lambda td: td.total_seconds(),
    Decimal: decimal_encoder,
    Enum: lambda obj: obj.value,
    frozenset: list,
    deque: list,
    GeneratorType: list,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    NameEmail: str,
    Path: str,
    Pattern: lambda obj: obj.pattern,
    SecretBytes: str,
    SecretStr: str,
    set: list,
    UUID: str,
}


def pydantic_encoder(obj: Any) -> Any:
    """JSON encoder that handles Pydantic models and dataclasses.

    Args:
        obj: The object to encode.

    Raises:
        TypeError: If the object is not JSON serializable.

    Returns:
        The encoded object.
    """
    from dataclasses import asdict, is_dataclass

    from pydantic import BaseModel

    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    elif is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)

    # Check the class type and its superclasses for a matching encoder
    for base in obj.__class__.__mro__[:-1]:
        try:
            encoder = ENCODERS_BY_TYPE[base]
        except KeyError:
            continue
        return encoder(obj)
    else:  # We have exited the for loop without finding a suitable encoder
        raise TypeError(
            f"Object of type '{obj.__class__.__name__}' is not JSON "
            f"serializable."
        )


# Keep the order, bool is a subclass of int so we need to check it first.
_PY_TYPE_TO_JSON_TYPE = (
    (bool, "boolean"),
    (int, "integer"),
    (float, "number"),
    (str, "string"),
    (list, "array"),
    (dict, "object"),
    (type(None), "null"),
)


def _json_type_of(value: Any) -> Optional[str]:
    """Returns the JSON Schema primitive type name for a Python value."""
    for py_type, name in _PY_TYPE_TO_JSON_TYPE:
        if isinstance(value, py_type):
            return name
    return None


def _schema_allowed_json_types(schema: Dict[str, Any]) -> Set[str]:
    """Returns the set of JSON Schema primitive types a schema accepts.

    Args:
        schema: JSON schema to inspect.

    Returns:
        Set of JSON type names (e.g. {"string", "integer"}).
    """
    types: Set[str] = set()

    node_type = schema.get("type")
    if isinstance(node_type, str):
        types.add(node_type)
    elif isinstance(node_type, list):
        types.update(t for t in node_type if isinstance(t, str))

    for key in ("anyOf", "oneOf", "allOf"):
        for variant in schema.get(key) or []:
            if isinstance(variant, dict):
                types.update(_schema_allowed_json_types(variant))

    return types


def parse_value_for_schema(
    raw_value: str,
    schema: Dict[str, Any],
) -> Any:
    """Parses a raw string input into a value compatible with a JSON schema.

    This does not perform a full JSON Schema validation. It only checks if the
    parsed **top-level type** matches the schema.

    If the parsed object does not match the schema and the schema accepts
    strings, the raw string is returned.

    Args:
        raw_value: The raw user input.
        schema: JSON schema.

    Raises:
        ValueError: If the input cannot be coerced to a value matching the
            schema's top-level types.

    Returns:
        The coerced value.
    """  # noqa: DOC503
    parse_error: Optional[json.JSONDecodeError] = None
    parsed: Any = None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as e:
        parse_error = e

    allowed = _schema_allowed_json_types(schema)

    if parse_error is None:
        if not allowed:
            return parsed
        parsed_type = _json_type_of(parsed)
        candidates = {parsed_type} if parsed_type else set()
        # JSON Schema: integers are also valid numbers.
        if parsed_type == "integer":
            candidates.add("number")
        if candidates & allowed:
            return parsed
        if "string" in allowed:
            return raw_value

        raise ValueError(
            f"Input does not match expected schema: got "
            f"{parsed_type}, expected one of {sorted(allowed)}."
        )

    if "string" in allowed or not allowed:
        return raw_value

    raise parse_error
