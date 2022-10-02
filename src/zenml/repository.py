#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Deprecated Repository implementation."""

from typing import Any, cast
from warnings import warn

from zenml.client import Client


class Repository:
    """DEPRECATED: Implementation of the ZenML repository instance."""

    def __new__(cls, *args: Any, **kwargs: Any) -> "Repository":
        """Returns the Client class due to deprecation.

        Args:
            *args: Arguments.
            **kwargs: Keyword arguments.

        Returns:
            Client: The Client class.
        """
        warn(
            f"{cls.__name__} has been renamed to {Client.__name__}, "
            f"the alias will be removed in the future.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cast(Repository, Client(*args, **kwargs))
