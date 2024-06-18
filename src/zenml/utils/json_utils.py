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
"""Carried over version of some functions from the pydantic v1 json module.

Check out the latest version here:
https://github.com/pydantic/pydantic/blob/v1.10.15/pydantic/json.py
"""

import datetime
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
from typing import Any, Callable, Dict, Type, Union
from uuid import UUID

from pydantic import NameEmail, SecretBytes, SecretStr
from pydantic.color import Color

__all__ = "pydantic_encoder"


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
    from dataclasses import asdict, is_dataclass

    from pydantic import BaseModel

    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif is_dataclass(obj):
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
