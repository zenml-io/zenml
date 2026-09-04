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
"""Unit tests for the software factory pipeline's fix loop guard."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import _validate_max_fix_iterations  # noqa: E402


@pytest.mark.parametrize("max_fix_iterations", [0, -1, -10])
def test_validate_max_fix_iterations_rejects_non_positive(
    max_fix_iterations: int,
) -> None:
    """`max_fix_iterations` below 1 must raise a clear `ValueError`."""
    with pytest.raises(
        ValueError, match="max_fix_iterations must be at least 1"
    ):
        _validate_max_fix_iterations(max_fix_iterations)


@pytest.mark.parametrize("max_fix_iterations", [1, 2, 10])
def test_validate_max_fix_iterations_accepts_positive(
    max_fix_iterations: int,
) -> None:
    """`max_fix_iterations` of 1 or more must be accepted without error."""
    _validate_max_fix_iterations(max_fix_iterations)
