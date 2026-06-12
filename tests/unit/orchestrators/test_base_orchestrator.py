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
from zenml.exceptions import HookExecutionException
from zenml.models import PipelineSnapshotResponse
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.steps.step_context import (
    RunContext,
    get_or_create_run_context,
    run_context_exists,
)


class _RunStepTestOrchestrator(BaseOrchestrator):
    def get_orchestrator_run_id(self) -> str:
        return "orchestrator-run-id"


def _snapshot_for_hook(init_hook_source=None, cleanup_hook_source=None):
    return SimpleNamespace(
        pipeline_configuration=SimpleNamespace(
            name="pipeline_name",
            environment={},
            init_hook_source=init_hook_source,
            init_hook_kwargs={"parameter": "value"},
            cleanup_hook_source=cleanup_hook_source,
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


def test_run_init_hook_returns_false_for_existing_context(mocker):
    run_context = get_or_create_run_context()
    run_context.initialize({"owner": "service"})
    mock_run_hook = mocker.patch(
        "zenml.orchestrators.base_orchestrator.run_hook"
    )

    result = BaseOrchestrator.run_init_hook(
        snapshot=_snapshot_for_hook(init_hook_source="module.hook")
    )

    assert result is False
    assert get_or_create_run_context().state == {"owner": "service"}
    mock_run_hook.assert_not_called()


def test_run_init_hook_returns_true_for_successful_hook(mocker):
    mock_run_hook = mocker.patch(
        "zenml.orchestrators.base_orchestrator.run_hook",
        return_value={"state": "from-hook"},
    )

    result = BaseOrchestrator.run_init_hook(
        snapshot=_snapshot_for_hook(init_hook_source="module.hook")
    )

    assert result is True
    assert get_or_create_run_context().state == {"state": "from-hook"}
    mock_run_hook.assert_called_once_with(
        "module.hook",
        kwargs={"parameter": "value"},
        track=False,
    )


def test_run_init_hook_runs_cleanup_and_clears_partial_context_when_hook_fails(
    mocker,
):
    mock_run_hook = mocker.patch(
        "zenml.orchestrators.base_orchestrator.run_hook",
        side_effect=[RuntimeError("init failed"), None],
    )

    with pytest.raises(HookExecutionException, match="Failed to execute"):
        BaseOrchestrator.run_init_hook(
            snapshot=_snapshot_for_hook(
                init_hook_source="module.init_hook",
                cleanup_hook_source="module.cleanup_hook",
            )
        )

    assert run_context_exists() is False
    assert mock_run_hook.call_args_list == [
        mocker.call(
            "module.init_hook",
            kwargs={"parameter": "value"},
            track=False,
        ),
        mocker.call("module.cleanup_hook", track=False),
    ]


def test_run_init_hook_preserves_init_error_when_partial_cleanup_fails(
    mocker,
):
    mocker.patch(
        "zenml.orchestrators.base_orchestrator.run_hook",
        side_effect=[
            RuntimeError("init failed"),
            RuntimeError("cleanup failed"),
        ],
    )
    mock_logger_error = mocker.patch(
        "zenml.orchestrators.base_orchestrator.logger.error"
    )

    with pytest.raises(HookExecutionException) as exc_info:
        BaseOrchestrator.run_init_hook(
            snapshot=_snapshot_for_hook(
                init_hook_source="module.init_hook",
                cleanup_hook_source="module.cleanup_hook",
            )
        )

    assert "Failed to execute init hook" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "init failed"
    assert run_context_exists() is False
    mock_logger_error.assert_called_once_with(
        "Failed to run cleanup hook: %s", mocker.ANY
    )


def test_run_init_hook_does_not_clear_initialized_context_when_hook_fails(
    mocker,
):
    RunContext().initialize({"owner": "service"})
    mock_run_hook = mocker.patch(
        "zenml.orchestrators.base_orchestrator.run_hook",
        side_effect=RuntimeError("hook failed"),
    )

    result = BaseOrchestrator.run_init_hook(
        snapshot=_snapshot_for_hook(init_hook_source="module.hook")
    )

    assert result is False
    assert RunContext().state == {"owner": "service"}
    mock_run_hook.assert_not_called()
