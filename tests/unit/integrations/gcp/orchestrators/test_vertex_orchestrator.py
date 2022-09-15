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

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import (
    DefaultContainerRegistryFlavor,
    GCPContainerRegistryFlavor,
)
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.azure.artifact_stores import AzureArtifactStore
from zenml.integrations.gcp.artifact_stores import GCPArtifactStore
from zenml.integrations.gcp.orchestrators import VertexOrchestrator
from zenml.stack import Stack


def test_vertex_orchestrator_attributes() -> None:
    """Tests that the basic attributes of the vertex orchestrator are set
    correctly."""
    orchestrator = VertexOrchestrator(
        name="",
        location="europe-west4",
        pipeline_root="gs://my-bucket/pipeline",
    )

    assert orchestrator.TYPE == StackComponentType.ORCHESTRATOR
    assert orchestrator.FLAVOR == "vertex"


def test_vertex_orchestrator_stack_validation() -> None:
    """Tests that the vertex orchestrator validates that it's stack has a
    container registry and that all stack components used are not local."""

    orchestrator = VertexOrchestrator(
        name="",
        location="europe-west4",
        pipeline_root="gs://my-bucket/pipeline",
    )
    orchestrator_no_pipeline_root = VertexOrchestrator(
        name="", location="europe-west4"
    )

    local_artifact_store = LocalArtifactStore(name="", path="/local/path")
    gcp_artifact_store = GCPArtifactStore(
        name="gcp_artifact_store", path="gs://my-bucket/artifacts"
    )
    azure_artifact_store = AzureArtifactStore(
        name="azure_artifact_store", path="abfs://my-container/artifacts"
    )

    local_container_registry = DefaultContainerRegistryFlavor(
        name="", uri="localhost:5000"
    )
    gcp_container_registry = GCPContainerRegistryFlavor(
        name="", uri="gcr.io/my-project"
    )

    with pytest.raises(StackValidationError):
        # any stack component is local
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
        ).validate()

    with pytest.raises(StackValidationError):
        # container registry is local
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # `pipeline_root` was not set and the artifact store is not a `GCPArtifactStore`
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator_no_pipeline_root,
            artifact_store=azure_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()

    with does_not_raise():
        # valid stack with container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()
