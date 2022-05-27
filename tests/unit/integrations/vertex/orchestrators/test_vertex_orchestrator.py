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

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import (
    DefaultContainerRegistry,
    GCPContainerRegistry,
)
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.gcp.artifact_stores import GCPArtifactStore
from zenml.integrations.vertex.orchestrators import VertexOrchestrator
from zenml.metadata_stores import MySQLMetadataStore, SQLiteMetadataStore
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
    local_metadata_store = SQLiteMetadataStore(name="", uri="./metadata.db")
    local_artifact_store = LocalArtifactStore(name="", path=".")
    mysql_metadata_store = MySQLMetadataStore(
        name="mysql_metadata_store",
        username="zenml",
        password="zenml",
        host="10.0.0.1",
        port="3306",
        database="zenml",
    )
    gcp_artifact_store = GCPArtifactStore(
        name="gcp_artifact_store", path="gs://my-bucket/artifacts"
    )

    local_container_registry = DefaultContainerRegistry(
        name="", uri="localhost:5000"
    )
    gcp_container_registry = GCPContainerRegistry(
        name="", uri="gcr.io/my-project"
    )

    with pytest.raises(StackValidationError):
        # any stack component is local
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=local_metadata_store,
            artifact_store=local_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=mysql_metadata_store,
            artifact_store=gcp_artifact_store,
        ).validate()

    with pytest.raises(StackValidationError):
        # container registry is local
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=mysql_metadata_store,
            artifact_store=gcp_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    with does_not_raise():
        # valid stack with container registry
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=mysql_metadata_store,
            artifact_store=gcp_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()
