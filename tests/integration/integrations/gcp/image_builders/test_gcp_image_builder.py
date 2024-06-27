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
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack

if TYPE_CHECKING:
    from zenml.integrations.gcp.flavors import GCPImageBuilderConfig
    from zenml.integrations.gcp.image_builders import GCPImageBuilder


def _get_gcp_image_builder(
    config: Optional["GCPImageBuilderConfig"] = None,
) -> "GCPImageBuilder":
    """Helper function to get a GCP image builder."""
    from zenml.integrations.gcp.flavors import GCPImageBuilderConfig
    from zenml.integrations.gcp.image_builders import GCPImageBuilder

    return GCPImageBuilder(
        name="",
        id=uuid4(),
        config=config or GCPImageBuilderConfig(),
        flavor="gcp",
        type=StackComponentType.IMAGE_BUILDER,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_stack_validation(
    local_orchestrator,
    local_artifact_store,
    local_container_registry,
    gcp_artifact_store,
    remote_container_registry,
) -> None:
    """Tests that the GCP image builder validates that it's stack has a remote
    container registry and artifact store."""

    image_builder = _get_gcp_image_builder()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=gcp_artifact_store,
            image_builder=image_builder,
        ).validate()

    with pytest.raises(StackValidationError):
        # local container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=gcp_artifact_store,
            image_builder=image_builder,
            container_registry=local_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # missing GCP artifact store
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            image_builder=image_builder,
            container_registry=remote_container_registry,
        ).validate()

    with does_not_raise():
        # valid stack with GCP container registry and GCP artifact store
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=gcp_artifact_store,
            image_builder=image_builder,
            container_registry=remote_container_registry,
        ).validate()
