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
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorConfig,
)
from zenml.integrations.kubernetes.step_operators import KubernetesStepOperator
from zenml.stack import Stack

K8S_CONTEXT = "kubernetes_context"


def _get_kubernetes_step_operator() -> KubernetesStepOperator:
    """Helper function to get a Kubernetes step operator."""
    return KubernetesStepOperator(
        name="",
        id=uuid4(),
        config=KubernetesStepOperatorConfig(
            kubernetes_context=K8S_CONTEXT,
        ),
        flavor="kubernetes",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _patch_k8s_clients(mocker):
    """Helper function to patch k8s clients."""

    mock_context = {"name": K8S_CONTEXT}

    def mock_load_kube_config(context: str) -> None:
        mock_context["name"] = context

    def mock_load_incluster_config() -> None:
        mock_context["name"] = "incluster"

    mocker.patch(
        "zenml.integrations.kubernetes.step_operators.kubernetes_step_operator.KubernetesStepOperator.get_kube_client",
        return_value=(None),
    )
    mocker.patch(
        "kubernetes.config.load_kube_config",
        side_effect=mock_load_kube_config,
    )
    mocker.patch(
        "kubernetes.config.load_incluster_config",
        side_effect=mock_load_incluster_config,
    )

    mocker.patch(
        "kubernetes.config.list_kube_config_contexts",
        return_value=([mock_context], mock_context),
    )

    mocker.patch("kubernetes.client.CoreV1Api")
    mocker.patch("kubernetes.client.BatchV1Api")
    mocker.patch("kubernetes.client.RbacAuthorizationV1Api")


def test_kubernetes_orchestrator_stack_validation(
    mocker,
    local_orchestrator,
    local_artifact_store,
    s3_artifact_store,
    remote_container_registry,
) -> None:
    """Test the kubernetes step operator with remote stacks."""
    _patch_k8s_clients(mocker)

    # Test remote stack with remote step operator
    step_operator = _get_kubernetes_step_operator()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
            step_operator=step_operator,
        ).validate()

    # Test with local artifact store
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            container_registry=remote_container_registry,
            step_operator=step_operator,
        ).validate()
