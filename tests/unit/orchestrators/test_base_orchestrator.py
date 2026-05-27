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
def _make_local_orchestrator():
    """Build a LocalOrchestrator without going through Stack/Client."""
    from datetime import datetime
    from uuid import uuid4

    from zenml.enums import StackComponentType
    from zenml.orchestrators.local.local_orchestrator import (
        LocalOrchestrator,
        LocalOrchestratorConfig,
    )

    return LocalOrchestrator(
        name="local",
        id=uuid4(),
        config=LocalOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _make_local_docker_orchestrator():
    """Build a LocalDockerOrchestrator (concrete ContainerizedOrchestrator)."""
    from datetime import datetime
    from uuid import uuid4

    from zenml.enums import StackComponentType
    from zenml.orchestrators.local_docker.local_docker_orchestrator import (
        LocalDockerOrchestrator,
        LocalDockerOrchestratorConfig,
    )

    return LocalDockerOrchestrator(
        name="local-docker",
        id=uuid4(),
        config=LocalDockerOrchestratorConfig(),
        flavor="local-docker",
        type=StackComponentType.ORCHESTRATOR,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


class TestInjectActiveStepImageEnv:
    """Tests for BaseOrchestrator._inject_active_step_image_env.

    Validates the contract used by the Sandbox ``STEP_IMAGE`` sentinel:
    containerized orchestrators export the env var; non-containerized
    ones skip silently; image-lookup failures degrade to a debug log.
    """

    def test_skips_for_non_containerized_orchestrator(self):
        from unittest.mock import MagicMock

        env = {"PRE_EXISTING": "1"}
        orchestrator = _make_local_orchestrator()
        orchestrator._inject_active_step_image_env(
            env, snapshot=MagicMock(), step_name="my_step"
        )
        assert "ZENML_ACTIVE_STEP_IMAGE" not in env
        assert env == {"PRE_EXISTING": "1"}

    def test_sets_for_containerized_orchestrator(self):
        from unittest.mock import MagicMock, patch

        env = {}
        orchestrator = _make_local_docker_orchestrator()
        with patch.object(
            type(orchestrator), "get_image", return_value="my-image:v1"
        ):
            orchestrator._inject_active_step_image_env(
                env, snapshot=MagicMock(), step_name="my_step"
            )
        assert env["ZENML_ACTIVE_STEP_IMAGE"] == "my-image:v1"

    def test_swallows_get_image_failure(self):
        from unittest.mock import MagicMock, patch

        env = {}
        orchestrator = _make_local_docker_orchestrator()
        with patch.object(
            type(orchestrator),
            "get_image",
            side_effect=RuntimeError("no build"),
        ):
            # Must not raise; falls through to flavor default at sandbox side.
            orchestrator._inject_active_step_image_env(
                env, snapshot=MagicMock(), step_name="my_step"
            )
        assert "ZENML_ACTIVE_STEP_IMAGE" not in env


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
