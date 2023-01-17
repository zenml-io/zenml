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
from typing import Optional
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    KubeflowOrchestratorConfig,
)
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
from zenml.stack import Stack


def _get_kubeflow_orchestrator(
    config: Optional[KubeflowOrchestratorConfig] = None,
) -> KubeflowOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return KubeflowOrchestrator(
        name="",
        id=uuid4(),
        config=config or KubeflowOrchestratorConfig(),
        flavor="kubeflow",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        project=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_kubeflow_orchestrator_stack_validation(
    mocker, local_artifact_store, local_container_registry
):
    """Tests that the kubeflow orchestrator validates that it's stack has a container registry."""
    mocker.patch(
        "zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator.get_kubernetes_contexts",
        return_value=([], ""),
    )

    orchestrator = _get_kubeflow_orchestrator()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()

    with does_not_raise():
        # valid stack with container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
