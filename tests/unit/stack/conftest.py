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
import pytest

from zenml.artifact_stores import BaseArtifactStore
from zenml.enums import StackComponentFlavor, StackComponentType
from zenml.metadata_stores import BaseMetadataStore
from zenml.orchestrators import BaseOrchestrator
from zenml.stack import Stack, StackComponent, StackValidator


class MockFlavor(StackComponentFlavor):
    """Flavor for mock components."""

    MOCK = "mock"


@pytest.fixture
def stack_with_mock_components(mocker):
    """Returns a stack instance with mocked components."""
    orchestrator = mocker.Mock(
        spec=BaseOrchestrator,
        type=StackComponentType.ORCHESTRATOR,
        flavor=MockFlavor.MOCK,
    )
    metadata_store = mocker.Mock(
        spec=BaseMetadataStore,
        type=StackComponentType.METADATA_STORE,
        flavor=MockFlavor.MOCK,
    )
    artifact_store = mocker.Mock(
        spec=BaseArtifactStore,
        type=StackComponentType.ARTIFACT_STORE,
        flavor=MockFlavor.MOCK,
    )

    return Stack(
        name="mock_stack",
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
    )


@pytest.fixture
def failing_stack_validator():
    """Returns a stack validator instance that always fails."""
    return StackValidator(custom_validation_function=lambda _: False)


@pytest.fixture
def stub_component():
    class _StubComponent(StackComponent):
        name = "StubComponent"
        supports_local_execution = False
        supports_remote_execution = False
        some_public_attribute_name = "Aria"
        _some_private_attribute_name = "Also Aria"

        @property
        def type(self) -> StackComponentType:
            return StackComponentType.ORCHESTRATOR

        @property
        def flavor(self) -> MockFlavor:
            return MockFlavor.MOCK

    return _StubComponent()
