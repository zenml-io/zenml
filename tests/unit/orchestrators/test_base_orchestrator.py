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
from zenml.models import PipelineSnapshotResponse
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig


class _RunStepTestOrchestrator(BaseOrchestrator):
    def get_orchestrator_run_id(self) -> str:
        return "orchestrator-run-id"


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


def test_run_step_passes_lifecycle_orchestrator(
    mocker,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    orchestrator = _RunStepTestOrchestrator.__new__(_RunStepTestOrchestrator)
    orchestrator._config = BaseOrchestratorConfig()
    orchestrator._active_snapshot = sample_snapshot_response_model

    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )
    mock_launch_step = mocker.patch("zenml.execution.step.utils.launch_step")

    orchestrator.run_step(step=step)

    mock_launch_step.assert_called_once_with(
        snapshot=sample_snapshot_response_model,
        step=step,
        orchestrator_run_id="orchestrator-run-id",
        retry=True,
        lifecycle_orchestrator=orchestrator,
    )
