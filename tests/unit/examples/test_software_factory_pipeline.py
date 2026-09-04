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
"""Unit tests for the `software_factory` example pipeline."""

import sys
from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).parents[3] / "examples" / "software_factory"


@pytest.fixture
def software_factory_entrypoint():
    """Import the pipeline's raw entrypoint function.

    The example package uses absolute imports (`from factory_utils import
    ...`), so its own directory needs to be on `sys.path` for the import to
    succeed. `software_factory.entrypoint` is the plain, undecorated
    function, so calling it directly exercises the validation logic without
    requiring an active ZenML run.

    Yields:
        The undecorated `software_factory` pipeline function.
    """
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        module_name = "software_factory_pipeline_under_test"
        sys.modules.pop(module_name, None)
        import importlib

        module = importlib.import_module("pipeline")
        yield module.software_factory.entrypoint
    finally:
        sys.path.remove(str(EXAMPLE_DIR))
        for name in ["pipeline", "factory_utils", "models"]:
            sys.modules.pop(name, None)


@pytest.mark.parametrize("max_fix_iterations", [0, -1])
def test_max_fix_iterations_below_one_raises(
    software_factory_entrypoint, max_fix_iterations
):
    """`max_fix_iterations` values below 1 raise a clear `ValueError`."""
    with pytest.raises(ValueError, match="max_fix_iterations"):
        software_factory_entrypoint(
            repo="owner/name",
            issue="some issue",
            target_branch="feature-branch",
            max_fix_iterations=max_fix_iterations,
        )
