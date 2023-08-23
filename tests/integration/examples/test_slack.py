#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
    """Runs the slack_alert example."""

    with run_example(
        request=request,
        name="slack",
        pipelines={"slack_post_pipeline": (1, 5)},
    ) as runs:
        run = runs["slack_post_pipeline"][0]
        alert_step = run.steps["alerter"]
        assert alert_step.output.load() is True
