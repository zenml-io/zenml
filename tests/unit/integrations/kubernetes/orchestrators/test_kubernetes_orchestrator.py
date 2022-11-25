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

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
)
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator
from zenml.stack import Stack


def _get_kubernetes_orchestrator() -> KubernetesOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return KubernetesOrchestrator(
        name="",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(skip_config_loading=True),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_kubernetes_orchestrator_remote_stack(
    remote_artifact_store, remote_container_registry
) -> None:
    """Test that the kubernetes orchestrator works with remote stacks."""
    orchestrator = _get_kubernetes_orchestrator()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubernetes_orchestrator_local_stack(
    local_artifact_store, local_container_registry
) -> None:
    """Test that the kubernetes orchestrator raises an error in local stacks."""
    orchestrator = _get_kubernetes_orchestrator()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
