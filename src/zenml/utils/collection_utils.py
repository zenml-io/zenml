#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Utilities for working with collections."""

from typing import Iterator, Sequence, TypeVar

T = TypeVar("T")


def batched(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Split a sequence into consecutive slices of at most `size` items.

    Args:
        items: The sequence to split.
        size: The maximum number of items per slice.

    Raises:
        ValueError: If `size` is not positive.

    Yields:
        The slices, in order. Nothing is yielded for an empty sequence.
    """
    if size < 1:
        raise ValueError("The batch size must be at least 1.")

    for offset in range(0, len(items), size):
        yield items[offset : offset + size]
