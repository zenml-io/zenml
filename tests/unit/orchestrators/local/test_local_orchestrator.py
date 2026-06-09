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

from zenml.enums import ExecutionMode, StackComponentType
from zenml.exceptions import HookExecutionException
from zenml.orchestrators import LocalOrchestratorFlavor
from zenml.steps.step_context import run_context_exists


def _pipeline_configuration(*, init_hook_source=None):
    return SimpleNamespace(
        name="local_pipeline",
        environment={},
        execution_mode=ExecutionMode.FAIL_FAST,
        init_hook_source=init_hook_source,
        init_hook_kwargs={},
        cleanup_hook_source=None,
    )


def test_local_orchestrator_flavor_attributes():
    """Tests that the local orchestrator flavor attributes are set."""
    flavor = LocalOrchestratorFlavor()
    assert flavor.type == StackComponentType.ORCHESTRATOR
    assert flavor.name == "local"


@pytest.mark.parametrize(
    "init_result, cleanup_expected",
    [
        (True, True),
        (False, False),
        (None, True),
    ],
)
def test_local_orchestrator_cleanup_depends_on_init_result(
    mocker,
    local_orchestrator,
    init_result,
    cleanup_expected,
):
    mock_run_init_hook = mocker.patch.object(
        local_orchestrator, "run_init_hook", return_value=init_result
    )
    mock_run_cleanup_hook = mocker.patch.object(
        local_orchestrator, "run_cleanup_hook"
    )
    snapshot = SimpleNamespace(
        pipeline_configuration=_pipeline_configuration(),
        step_configurations={},
    )

    local_orchestrator.submit_pipeline(
        snapshot=snapshot,
        stack=mocker.MagicMock(),
        base_environment={},
        step_environments={},
    )

    mock_run_init_hook.assert_called_once_with(snapshot=snapshot)
    if cleanup_expected:
        mock_run_cleanup_hook.assert_called_once_with(snapshot=snapshot)
    else:
        mock_run_cleanup_hook.assert_not_called()


def test_local_orchestrator_clears_partial_run_context_when_init_raises(
    mocker,
    local_orchestrator,
):
    mocker.patch(
        "zenml.orchestrators.base_orchestrator.load_and_run_hook",
        side_effect=RuntimeError("init failed"),
    )
    snapshot = SimpleNamespace(
        pipeline_configuration=_pipeline_configuration(
            init_hook_source="module.init_hook"
        ),
        step_configurations={},
    )

    with pytest.raises(HookExecutionException, match="Failed to execute"):
        local_orchestrator.submit_pipeline(
            snapshot=snapshot,
            stack=mocker.MagicMock(),
            base_environment={},
            step_environments={},
        )

    assert run_context_exists() is False
