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
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.stack import Stack


def test_kubeflow_orchestrator_attributes():
    """Tests that the basic attributes of the kubeflow orchestrator are set
    correctly."""
    orchestrator = KubeflowOrchestrator(name="")

    assert orchestrator.TYPE == StackComponentType.ORCHESTRATOR
    assert orchestrator.FLAVOR == "kubeflow"


def test_kubeflow_orchestrator_stack_validation():
    """Tests that the kubeflow orchestrator validates that it's stack has a
    container registry."""
    orchestrator = KubeflowOrchestrator(name="")
    metadata_store = SQLiteMetadataStore(name="", uri="./metadata.db")
    artifact_store = LocalArtifactStore(name="", path=".")
    container_registry = BaseContainerRegistry(name="", uri="")

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
        )

    with does_not_raise():
        # valid stack with container registry
        Stack(
            name="",
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
            container_registry=container_registry,
        )
