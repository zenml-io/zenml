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
"""Utility functions for handling UUIDs."""

import hashlib
from typing import Any, Optional, Union
from uuid import UUID


def is_valid_uuid(value: Any, version: int = 4) -> bool:
    """Checks if a string is a valid UUID.

    Args:
        value: String to check.
        version: Version of UUID to check for.

    Returns:
        True if string is a valid UUID, False otherwise.
    """
    if isinstance(value, UUID):
        return True
    if isinstance(value, str):
        try:
            UUID(value, version=version)
            return True
        except ValueError:
            return False
    return False


def parse_name_or_uuid(
    name_or_id: Optional[str],
) -> Optional[Union[str, UUID]]:
    """Convert a "name or id" string value to a string or UUID.

    Args:
        name_or_id: Name or id to convert.

    Returns:
        A UUID if name_or_id is a UUID, string otherwise.
    """
    if name_or_id:
        try:
            return UUID(name_or_id)
        except ValueError:
            return name_or_id
    else:
        return name_or_id


def generate_uuid_from_string(value: str) -> UUID:
    """Deterministically generates a UUID from a string seed.

    Args:
        value: The string from which to generate the UUID.

    Returns:
        The generated UUID.
    """
    hash_ = hashlib.md5()
    hash_.update(value.encode("utf-8"))
    return UUID(hex=hash_.hexdigest(), version=4)
