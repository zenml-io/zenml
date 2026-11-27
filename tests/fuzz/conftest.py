#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Configuration shared only by explicitly selected fuzz tests."""

import os
import signal
from pathlib import Path
from types import FrameType
from typing import NoReturn, Optional

import pytest

if os.environ.get("ZENML_FUZZ") != "1":
    raise pytest.UsageError(
        "Fuzz tests are opt-in. Run them through `python scripts/fuzz.py`."
    )

try:
    from hypothesis import settings
    from hypothesis.database import DirectoryBasedExampleDatabase
except ModuleNotFoundError as error:
    raise pytest.UsageError(
        "Hypothesis is required for fuzz tests. Install "
        "tests/fuzz/requirements.txt beside the editable checkout."
    ) from error


def _terminate_with_cleanup(
    _signum: int, _frame: Optional[FrameType]
) -> NoReturn:
    """Interrupt pytest so fixture finalizers run after runner termination."""
    raise KeyboardInterrupt


if os.name == "posix":
    signal.signal(signal.SIGTERM, _terminate_with_cleanup)


def _example_database() -> DirectoryBasedExampleDatabase:
    """Return a directory-backed Hypothesis database that works on CI.

    Hypothesis auto-activates its built-in ``ci`` profile on GitHub Actions,
    which sets ``database=None`` and ``derandomize=True``. Passing an explicit
    database and ``derandomize=False`` below ensures hosted fuzz runs explore
    fresh inputs and save failing examples to the cached corpus directory.

    Returns:
        A directory-backed Hypothesis example database.
    """
    configured = os.environ.get("HYPOTHESIS_STORAGE_DIRECTORY")
    if configured:
        return DirectoryBasedExampleDatabase(Path(configured) / "examples")
    return DirectoryBasedExampleDatabase(Path(".hypothesis") / "examples")


_EXAMPLE_DATABASE = _example_database()

for profile_name, max_examples in (
    ("local", 25),
    ("pr", 100),
    ("nightly", 500),
):
    settings.register_profile(
        profile_name,
        max_examples=max_examples,
        deadline=None,
        derandomize=False,
        database=_EXAMPLE_DATABASE,
        print_blob=True,
    )
