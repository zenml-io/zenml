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
import os
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.artifact_stores import BaseArtifactStore
from zenml.constants import ENV_ZENML_SKIP_IMAGE_BUILDER_DEFAULT
from zenml.enums import StackComponentType
from zenml.orchestrators import BaseOrchestrator
from zenml.stack import Stack, StackComponent, StackValidator
from zenml.stack.stack_component import StackComponentConfig

MOCK_FLAVOR = "mock_flavor"


@pytest.fixture
def stack_with_mock_components(mocker):
    """Returns a stack instance with mocked components."""
    mocker.patch.dict(
        os.environ, {ENV_ZENML_SKIP_IMAGE_BUILDER_DEFAULT: "True"}
    )
    orchestrator = mocker.Mock(
        spec=BaseOrchestrator,
        type=StackComponentType.ORCHESTRATOR,
        flavor=MOCK_FLAVOR,
    )
    artifact_store = mocker.Mock(
        spec=BaseArtifactStore,
        type=StackComponentType.ARTIFACT_STORE,
        flavor=MOCK_FLAVOR,
        path="/",
    )
    orchestrator.config.required_secrets = set()
    orchestrator.settings_class = None
    orchestrator.config.is_remote = False
    orchestrator.get_docker_builds.return_value = []

    artifact_store.config.required_secrets = set()
    artifact_store.settings_class = None
    artifact_store.config.path = "/"
    artifact_store.get_docker_builds.return_value = []

    return Stack(
        id=uuid4(),
        name="mock_stack",
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )


@pytest.fixture
def failing_stack_validator():
    """Returns a stack validator instance that always fails."""
    return StackValidator(
        custom_validation_function=lambda _: (False, "Error")
    )


@pytest.fixture
def stub_component_config():
    class _StubComponentConfig(StackComponentConfig):
        some_public_attribute_name: str = "Aria"
        _some_private_attribute_name: str = "Also Aria"

    return _StubComponentConfig()


@pytest.fixture
def stub_component():
    class _StubComponentConfig(StackComponentConfig):
        some_public_attribute_name: str = "Aria"
        _some_private_attribute_name: str = "Also Aria"

    class _StubComponent(StackComponent):
        @property
        def config(self) -> _StubComponentConfig:
            return self._config

    return _StubComponent(
        name="StubComponent",
        id=uuid4(),
        config=_StubComponentConfig(),
        flavor=MOCK_FLAVOR,
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
