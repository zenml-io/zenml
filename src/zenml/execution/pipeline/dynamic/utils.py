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
"""Dynamic pipeline execution utilities."""

from typing import (
    Generic,
    TypeVar,
)

T = TypeVar("T")


class _Unmapped(Generic[T]):
    """Wrapper class for inputs that should not be mapped over."""

    def __init__(self, value: T):
        """Initialize the wrapper.

        Args:
            value: The value to wrap.
        """
        self.value = value


def unmapped(value: T) -> _Unmapped[T]:
    """Helper function to pass an input without mapping over it.

    Wrap any step input with this function and then pass it to `step.map(...)`
    to pass the full value to all steps.

    Args:
        value: The value to wrap.

    Returns:
        The wrapped value.
    """
    return _Unmapped(value)
