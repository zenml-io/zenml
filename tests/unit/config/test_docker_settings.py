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
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from zenml.config.docker_settings import (
    DockerSettings,
    _docker_settings_warnings_logged,
)
from zenml.orchestrators import ContainerizedOrchestrator


def test_build_skipping():
    """Tests that a parent image is required when setting `skip_build` to
    `True`."""
    with pytest.raises(ValidationError):
        DockerSettings(skip_build=True)

    with does_not_raise():
        DockerSettings(skip_build=False)
        DockerSettings(skip_build=True, parent_image="my_parent_image")


def test_generated_warnings():
    from zenml.client import Client

    if isinstance(
        Client().active_stack.orchestrator, ContainerizedOrchestrator
    ):
        pytest.skip(reason="Check warning generation for local orchestrators")

    if "non_containerized_orchestrator" in _docker_settings_warnings_logged:
        _docker_settings_warnings_logged.remove(
            "non_containerized_orchestrator"
        )

    with pytest.warns(UserWarning) as warning:
        DockerSettings()

        assert (
            "You are specifying docker settings without a containerized orchestrator"
            in str(warning[0].message)
        )

    with pytest.warns(None):
        DockerSettings()

    assert "non_containerized_orchestrator" in _docker_settings_warnings_logged
