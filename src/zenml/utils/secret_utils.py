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
from typing import Any, NamedTuple

_secret_reference_expression = re.compile(r"\$\{ ?\S+?\.\S+ ?\}")


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
    reference = reference[:-1]
    reference = reference.strip()

    secret_name, secret_key = reference.split(".", 1)
    return SecretReference(name=secret_name, key=secret_key)
