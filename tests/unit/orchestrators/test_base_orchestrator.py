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
from types import SimpleNamespace

import pytest

from zenml.config import ResourceSettings
from zenml.config.step_configurations import Step
from zenml.models import PipelineSnapshotResponse
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.steps.step_context import get_or_create_run_context


class _RunStepTestOrchestrator(BaseOrchestrator):
    def get_orchestrator_run_id(self) -> str:
        return "orchestrator-run-id"


def _snapshot_for_hook(init_hook_source=None):
    return SimpleNamespace(
        pipeline_configuration=SimpleNamespace(
            name="pipeline_name",
            environment={},
            init_hook_source=init_hook_source,
            init_hook_kwargs={"parameter": "value"},
        )
    )


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


def test_run_step_launches_without_extra_lifecycle_argument(
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
    )


def test_run_init_hook_returns_true_for_fresh_context_without_hook():
    result = BaseOrchestrator.run_init_hook(snapshot=_snapshot_for_hook())

    assert result is True
    run_context = get_or_create_run_context()
    assert run_context.initialized is True
    assert run_context.state is None


def test_run_init_hook_returns_false_for_existing_context():
    run_context = get_or_create_run_context()
    run_context.initialize({"owner": "service"})

    result = BaseOrchestrator.run_init_hook(snapshot=_snapshot_for_hook())

    assert result is False
    assert get_or_create_run_context().state == {"owner": "service"}


def test_run_init_hook_returns_true_for_successful_hook(mocker):
    mock_load_and_run_hook = mocker.patch(
        "zenml.orchestrators.base_orchestrator.load_and_run_hook",
        return_value={"state": "from-hook"},
    )

    result = BaseOrchestrator.run_init_hook(
        snapshot=_snapshot_for_hook(init_hook_source="module.hook")
    )

    assert result is True
    assert get_or_create_run_context().state == {"state": "from-hook"}
    mock_load_and_run_hook.assert_called_once_with(
        "module.hook",
        hook_parameters={"parameter": "value"},
        raise_on_error=True,
    )
