#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Cache policy."""

from typing import Any, List, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field
from typing_extensions import Annotated

from zenml.logger import get_logger

logger = get_logger(__name__)


class CachePolicy(BaseModel):
    """Cache policy."""

    include_step_code: bool = Field(
        default=True,
        description="Whether to include the step code in the cache key.",
    )
    include_step_parameters: bool = Field(
        default=True,
        description="Whether to include the step parameters in the cache key.",
    )
    include_artifact_values: bool = Field(
        default=True,
        description="Whether to include the artifact values in the cache key. "
        "If the materializer for an artifact doesn't support generating a "
        "content hash, the artifact ID will be used as a fallback if enabled.",
    )
    include_artifact_ids: bool = Field(
        default=True,
        description="Whether to include the artifact IDs in the cache key.",
    )
    ignored_inputs: Optional[List[str]] = Field(
        default=None,
        description="List of input names to ignore in the cache key.",
    )

    @classmethod
    def default(cls) -> "CachePolicy":
        """Default cache policy.

        Returns:
            The default cache policy.
        """
        return cls(
            include_step_code=True,
            include_step_parameters=True,
            include_artifact_values=True,
            include_artifact_ids=True,
            ignored_inputs=None,
        )

    @classmethod
    def from_string(cls, value: str) -> "CachePolicy":
        """Create a cache policy from a string.

        Args:
            value: The string to create a cache policy from.

        Raises:
            ValueError: If the string is not a valid cache policy.

        Returns:
            The cache policy.
        """
        if value.lower() == "default":
            return cls.default()
        else:
            raise ValueError(f"Invalid cache policy: {value}")


def _convert_cache_policy(value: Any) -> Any:
    """Converts a potential cache policy string to a cache policy object.

    Args:
        value: The value to convert.

    Returns:
        The converted value.
    """
    if isinstance(value, str):
        return CachePolicy.from_string(value)

    return value


CachePolicyWithValidator = Annotated[
    CachePolicy, BeforeValidator(_convert_cache_policy)
]
CachePolicyOrString = Union[CachePolicy, str]
