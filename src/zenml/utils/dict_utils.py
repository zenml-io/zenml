#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Util functions for dictionaries."""

import base64
import json
from typing import Any, Dict, TypeVar

from zenml.utils.json_utils import pydantic_encoder

K = TypeVar("K")
V = TypeVar("V")


class BoundedDict(Dict[K, V]):
    """Dictionary that evicts the oldest entries beyond a maximum size."""

    def __init__(self, max_size: int) -> None:
        """Initialize the dictionary.

        Args:
            max_size: The maximum number of entries to retain.

        Raises:
            ValueError: If `max_size` is not greater than 0.
        """
        if max_size <= 0:
            raise ValueError("max_size must be greater than 0")

        super().__init__()
        self._max_size = max_size

    def __setitem__(self, key: K, value: V) -> None:
        """Set an entry and evict the oldest entries beyond the size limit.

        Args:
            key: The entry key.
            value: The entry value.
        """
        super().__setitem__(key, value)
        self._evict()

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update the dictionary and evict the oldest entries beyond the limit.

        Args:
            *args: Positional arguments for the update.
            **kwargs: Keyword arguments for the update.
        """
        super().update(*args, **kwargs)
        self._evict()

    def _evict(self) -> None:
        """Evict the oldest entries beyond the maximum size."""
        while len(self) > self._max_size:
            del self[next(iter(self))]


def recursive_update(
    original: Dict[str, Any], update: Dict[str, Any], ignore_none: bool = False
) -> Dict[str, Any]:
    """Recursively updates a dictionary.

    Args:
        original: The dictionary to update.
        update: The dictionary containing the updated values.
        ignore_none: Ignore `None` values in the update.

    Returns:
        The updated dictionary.
    """
    for key, value in update.items():
        if ignore_none and value is None:
            continue
        if isinstance(value, Dict):
            original_value = original.get(key, None) or {}
            if isinstance(original_value, Dict):
                original[key] = recursive_update(
                    original_value, value, ignore_none
                )
            else:
                original[key] = value
        else:
            original[key] = value
    return original


def remove_none_values(
    dict_: Dict[str, Any], recursive: bool = False
) -> Dict[str, Any]:
    """Removes all key-value pairs with `None` value.

    Args:
        dict_: The dict from which the key-value pairs should be removed.
        recursive: If `True`, will recursively remove `None` values in all
            child dicts.

    Returns:
        The updated dictionary.
    """

    def _maybe_recurse(value: Any) -> Any:
        """Calls `remove_none_values` recursively if required.

        Args:
            value: A dictionary value.

        Returns:
            The updated dictionary value.
        """
        if recursive and isinstance(value, Dict):
            return remove_none_values(value, recursive=True)
        else:
            return value

    return {k: _maybe_recurse(v) for k, v in dict_.items() if v is not None}


def dict_to_bytes(dict_: Dict[str, Any]) -> bytes:
    """Converts a dictionary to bytes.

    Args:
        dict_: The dictionary to convert.

    Returns:
        The dictionary as bytes.
    """
    return base64.b64encode(
        json.dumps(
            dict_,
            sort_keys=False,
            default=pydantic_encoder,
        ).encode("utf-8")
    )
