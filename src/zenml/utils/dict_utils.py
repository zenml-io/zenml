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
from typing import Any, Dict

from zenml.utils.json_utils import pydantic_encoder


def recursive_update(
    original: Dict[str, Any], update: Dict[str, Any]
) -> Dict[str, Any]:
    """Recursively updates a dictionary.

    Args:
        original: The dictionary to update.
        update: The dictionary containing the updated values.

    Returns:
        The updated dictionary.
    """
    for key, value in update.items():
        if isinstance(value, Dict):
            original_value = original.get(key, None) or {}
            if isinstance(original_value, Dict):
                original[key] = recursive_update(original_value, value)
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
