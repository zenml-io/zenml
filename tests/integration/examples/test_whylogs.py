#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import pytest

from tests.integration.examples.utils import run_example


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the whylogs_data_profiling example."""
    from whylogs.core import DatasetProfileView  # type: ignore

    with run_example(
        request=request,
        name="whylogs",
        pipelines={"data_profiling_pipeline": (1, 4)},
    ) as runs:
        steps = runs["data_profiling_pipeline"][0].steps
        profiles = [
            steps["data_loader"].outputs["profile"][0].load(),
            steps["whylogs_profiler_step"].output.load(),
            steps["whylogs_profiler_step_2"].output.load(),
        ]

        for profile in profiles:
            assert isinstance(profile, DatasetProfileView)
