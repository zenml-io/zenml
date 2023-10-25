#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utility functions for secrets and secret references."""
import re
from typing import TYPE_CHECKING, Any, NamedTuple

from pydantic import Field

if TYPE_CHECKING:
    from pydantic.fields import ModelField

_secret_reference_expression = re.compile(r"\{\{\s*\S+?\.\S+\s*\}\}")

PYDANTIC_SENSITIVE_FIELD_MARKER = "sensitive"
PYDANTIC_CLEAR_TEXT_FIELD_MARKER = "prevent_secret_reference"


def is_secret_reference(value: Any) -> bool:
    """Checks whether any value is a secret reference.

    Args:
        value: The value to check.

    Returns:
        `True` if the value is a secret reference, `False` otherwise.
    """
    if not isinstance(value, str):
        return False

    return bool(_secret_reference_expression.fullmatch(value))


class SecretReference(NamedTuple):
    """Class representing a secret reference.

    Attributes:
        name: The secret name.
        key: The secret key.
    """

    name: str
    key: str


def parse_secret_reference(reference: str) -> SecretReference:
    """Parses a secret reference.

    This function assumes the input string is a valid secret reference and
    **does not** perform any additional checks. If you pass an invalid secret
    reference here, this will most likely crash.

    Args:
        reference: The string representing a **valid** secret reference.

    Returns:
        The parsed secret reference.
    """
    reference = reference[2:]
    reference = reference[:-2]

    secret_name, secret_key = reference.split(".", 1)
    secret_name, secret_key = secret_name.strip(), secret_key.strip()
    return SecretReference(name=secret_name, key=secret_key)


def SecretField(*args: Any, **kwargs: Any) -> Any:
    """Marks a pydantic field as something containing sensitive information.

    Args:
        *args: Positional arguments which will be forwarded
            to `pydantic.Field(...)`.
        **kwargs: Keyword arguments which will be forwarded to
            `pydantic.Field(...)`.

    Returns:
        Pydantic field info.
    """
    kwargs[PYDANTIC_SENSITIVE_FIELD_MARKER] = True
    return Field(*args, **kwargs)  # type: ignore[pydantic-field]


def ClearTextField(*args: Any, **kwargs: Any) -> Any:
    """Marks a pydantic field to prevent secret references.

    Args:
        *args: Positional arguments which will be forwarded
            to `pydantic.Field(...)`.
        **kwargs: Keyword arguments which will be forwarded to
            `pydantic.Field(...)`.

    Returns:
        Pydantic field info.
    """
    kwargs[PYDANTIC_CLEAR_TEXT_FIELD_MARKER] = True
    return Field(*args, **kwargs)  # type: ignore[pydantic-field]


def is_secret_field(field: "ModelField") -> bool:
    """Returns whether a pydantic field contains sensitive information or not.

    Args:
        field: The field to check.

    Returns:
        `True` if the field contains sensitive information, `False` otherwise.
    """
    return field.field_info.extra.get(PYDANTIC_SENSITIVE_FIELD_MARKER, False)  # type: ignore[no-any-return]


def is_clear_text_field(field: "ModelField") -> bool:
    """Returns whether a pydantic field prevents secret references or not.

    Args:
        field: The field to check.

    Returns:
        `True` if the field prevents secret references, `False` otherwise.
    """
    return field.field_info.extra.get(PYDANTIC_CLEAR_TEXT_FIELD_MARKER, False)  # type: ignore[no-any-return]
