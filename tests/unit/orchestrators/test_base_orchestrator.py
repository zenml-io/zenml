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

from zenml.config import ResourceSettings
from zenml.config.step_configurations import Step
from zenml.orchestrators import BaseOrchestrator


@pytest.mark.parametrize(
    "step_operator, settings, resources_required",
    [
        ("step_operator", {}, False),
        (None, {}, False),
        (None, {"resources": ResourceSettings()}, False),
        (None, {"resources": ResourceSettings(cpu_count=1)}, True),
    ],
)
def test_resource_required(step_operator, settings, resources_required):
    """Tests whether the resource requirements detection method works as
    expected."""
    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {},
            },
            "config": {
                "name": "step_name",
                "enable_cache": True,
                "step_operator": step_operator,
                "settings": settings,
            },
        }
    )
    assert (
        BaseOrchestrator.requires_resources_in_orchestration_environment(
            step=step
        )
        is resources_required
    )
