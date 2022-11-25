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

from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
    BaseContainerRegistryConfig,
)
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.github.flavors.github_actions_orchestrator_flavor import (
    GitHubActionsOrchestratorConfig,
)
from zenml.integrations.github.orchestrators import GitHubActionsOrchestrator
from zenml.stack import Stack


def _get_github_actions_orchestrator() -> GitHubActionsOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return GitHubActionsOrchestrator(
        name="",
        id=uuid4(),
        config=GitHubActionsOrchestratorConfig(),
        flavor="github",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_github_actions_orchestrator_stack_validation(
    local_container_registry,
    remote_container_registry,
    local_artifact_store,
    remote_artifact_store,
) -> None:
    """Tests the GitHub actions orchestrator stack validation."""
    orchestrator = _get_github_actions_orchestrator()

    container_registry_that_requires_authentication = BaseContainerRegistry(
        name="",
        id=uuid4(),
        config=BaseContainerRegistryConfig(
            uri="localhost:5000", authentication_secret="some_secret"
        ),
        flavor="default",
        type=StackComponentType.CONTAINER_REGISTRY,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    with does_not_raise():
        # Stack with container registry and only remote components
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # Stack without container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
        ).validate()

    with pytest.raises(StackValidationError):
        # Stack with local container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # Stack with container registry that requires authentication
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=container_registry_that_requires_authentication,
        ).validate()

    with pytest.raises(StackValidationError):
        # Stack with local components
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=remote_container_registry,
        ).validate()
