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
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator

K8S_CONTEXT = "kubeflow_context"


def _get_kubeflow_orchestrator(
    local: bool = False, skip_local_validations: bool = False
) -> "KubeflowOrchestrator":
    """Helper function to get a Kubeflow orchestrator."""

    from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
        KubeflowOrchestratorConfig,
    )
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator

    return KubeflowOrchestrator(
        name="",
        id=uuid4(),
        config=KubeflowOrchestratorConfig(
            kubernetes_context=K8S_CONTEXT,
            local=local,
            skip_local_validations=skip_local_validations,
        ),
        flavor="kubeflow",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_kubeflow_orchestrator_remote_stack(
    mocker, s3_artifact_store, remote_container_registry
) -> None:
    """Test the remote and local kubeflow orchestrator with remote stacks."""
    mocker.patch(
        "zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_CONTEXT], K8S_CONTEXT),
    )

    # Test remote stack with remote orchestrator
    orchestrator = _get_kubeflow_orchestrator()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    # Test remote stack with local orchestrator
    orchestrator = _get_kubeflow_orchestrator(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()
    orchestrator = _get_kubeflow_orchestrator(
        local=True, skip_local_validations=True
    )
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubeflow_orchestrator_local_stack(
    mocker, local_artifact_store, local_container_registry
) -> None:
    """Test the remote and local kubeflow orchestrator with remote stacks."""
    mocker.patch(
        "zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_CONTEXT], K8S_CONTEXT),
    )

    # Test missing container registry
    orchestrator = _get_kubeflow_orchestrator(local=True)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()

    # Test local stack with remote orchestrator
    orchestrator = _get_kubeflow_orchestrator()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    orchestrator = _get_kubeflow_orchestrator(skip_local_validations=True)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
