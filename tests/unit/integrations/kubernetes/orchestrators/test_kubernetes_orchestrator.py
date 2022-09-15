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
from uuid import uuid4

import pytest

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.container_registries import DefaultContainerRegistryFlavor
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.gcp.artifact_stores import GCPArtifactStore
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator
from zenml.stack import Stack


def test_kubernetes_orchestrator_attributes() -> None:
    """Test that the Kubernetes orchestrator has correct type and flavor."""
    orchestrator = KubernetesOrchestrator(name="", skip_config_loading=True)
    assert orchestrator.TYPE == StackComponentType.ORCHESTRATOR
    assert orchestrator.FLAVOR == "kubernetes"


def test_kubernetes_orchestrator_remote_stack() -> None:
    """Test that the kubernetes orchestrator works with remote stacks."""
    orchestrator = KubernetesOrchestrator(name="", skip_config_loading=True)
    remote_container_registry = DefaultContainerRegistryFlavor(
        name="", uri="gcr.io/my-project"
    )
    remote_artifact_store = GCPArtifactStore(name="", path="gs://bucket")
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubernetes_orchestrator_local_stack() -> None:
    """Test that the kubernetes orchestrator raises an error in local stacks."""
    orchestrator = KubernetesOrchestrator(name="", skip_config_loading=True)
    local_container_registry = DefaultContainerRegistryFlavor(
        name="", uri="localhost:5000"
    )
    local_artifact_store = LocalArtifactStore(name="", path="artifacts/")
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
