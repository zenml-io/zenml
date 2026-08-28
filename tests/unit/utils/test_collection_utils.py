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
"""Tests for the collection utilities."""

import pytest

from zenml.utils.collection_utils import batched


@pytest.mark.parametrize(
    "items, size, expected",
    [
        ([], 3, []),
        ([1, 2], 3, [[1, 2]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2, 3, 4], 3, [[1, 2, 3], [4]]),
        ("abcde", 2, ["ab", "cd", "e"]),
    ],
)
def test_batched_yields_consecutive_slices(
    items: list[int], size: int, expected: list[list[int]]
) -> None:
    """Every item ends up in exactly one slice, in order."""
    assert list(batched(items, size)) == expected


def test_batched_rejects_non_positive_sizes() -> None:
    """A size below one would never terminate."""
    with pytest.raises(ValueError):
        next(batched([1], 0))
