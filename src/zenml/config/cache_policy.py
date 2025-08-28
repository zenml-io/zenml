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

from typing import Any, Union

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

from zenml.logger import get_logger

logger = get_logger(__name__)


class CachePolicy(BaseModel):
    """Cache policy."""

    include_step_code: bool = True
    include_artifact_values: bool = True

    @classmethod
    def default(cls) -> "CachePolicy":
        """Default cache policy.

        Returns:
            The default cache policy.
        """
        return cls(include_step_code=True, include_artifact_values=True)

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
    if isinstance(value, str):
        return CachePolicy.from_string(value)

    return value


CachePolicyWithValidator = Annotated[
    CachePolicy, BeforeValidator(_convert_cache_policy)
]
CachePolicyOrString = Union[CachePolicy, str]
