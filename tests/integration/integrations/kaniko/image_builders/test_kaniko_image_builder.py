#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from zenml.integrations.kaniko.flavors.kaniko_image_builder_flavor import (
    KanikoImageBuilderConfig,
)
from zenml.integrations.kaniko.image_builders import KanikoImageBuilder
from zenml.stack import Stack


def _get_kaniko_image_builder(
    config: Optional[KanikoImageBuilderConfig] = None,
) -> KanikoImageBuilder:
    """Helper function to get a Kaniko image builder."""
    return KanikoImageBuilder(
        name="",
        id=uuid4(),
        config=config or KanikoImageBuilderConfig(kubernetes_context=""),
        flavor="kaniko",
        type=StackComponentType.IMAGE_BUILDER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_stack_validation(
    local_orchestrator,
    local_artifact_store,
    local_container_registry,
    s3_artifact_store,
    remote_container_registry,
):
    """Tests that the Kaniko image builder validates that it's stack has a
    remote container registry and artifact store."""

    image_builder = _get_kaniko_image_builder()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            image_builder=image_builder,
        ).validate()

    with pytest.raises(StackValidationError):
        # local container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
            image_builder=image_builder,
        ).validate()

    with does_not_raise():
        # valid stack with remote container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            container_registry=remote_container_registry,
            image_builder=image_builder,
        ).validate()

    config = KanikoImageBuilderConfig(
        kubernetes_context="", store_context_in_artifact_store=True
    )
    image_builder_that_requires_remote_artifact_store = (
        _get_kaniko_image_builder(config=config)
    )

    with pytest.raises(StackValidationError):
        # local artifact store
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            container_registry=remote_container_registry,
            image_builder=image_builder_that_requires_remote_artifact_store,
        ).validate()

    with does_not_raise():
        # valid stack with remote artifact store
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
            image_builder=image_builder_that_requires_remote_artifact_store,
        ).validate()
