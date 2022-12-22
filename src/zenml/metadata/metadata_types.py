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
"""Custom types that can be used as metadata of ZenML artifacts."""

from typing import Union


class Uri(str):
    """Special string class to indicate a URI."""


class DType(str):
    """Special string class to indicate a data type."""


def human_readable_size(num_bytes: int) -> str:
    """Converts a number of bytes to a human-readable string.

    Args:
        num_bytes: The number of bytes.

    Returns:
        A human-readable string representation of the data size.
    """
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(num_bytes) < 1000:
            return f"{num_bytes}{unit}"
        num_bytes = num_bytes // 1000
    return f"{num_bytes}YB"


class StorageSize(int):
    """Storage size of an artifact in number of bytes."""

    def __str__(self) -> str:
        """Get a string representation of the storage size.

        Returns:
            A human-readable string representation of the storage size.
        """
        return human_readable_size(int(self))


# Union of all types that can be used as metadata.
# We don't use subscripted generics here because they cannot be used for
# `isinstance` checks.
MetadataType = Union[
    str,
    int,
    float,
    bool,
    dict,
    list,
    set,
    tuple,  # type: ignore[type-arg]
    Uri,
    DType,
    StorageSize,
]
