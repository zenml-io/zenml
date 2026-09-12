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

import pytest

if os.environ.get("ZENML_FUZZ") != "1":
    raise pytest.UsageError(
        "Fuzz tests are opt-in. Run them through `python scripts/fuzz.py`."
    )

try:
    from hypothesis import settings
except ModuleNotFoundError as error:
    raise pytest.UsageError(
        "Hypothesis is required for fuzz tests. Install "
        "tests/fuzz/requirements.txt beside the editable checkout."
    ) from error


for profile_name, max_examples in (
    ("local", 25),
    ("pr", 100),
    ("nightly", 500),
):
    settings.register_profile(
        profile_name,
        max_examples=max_examples,
        print_blob=True,
    )
