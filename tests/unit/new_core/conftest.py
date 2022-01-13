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

from zenml.enums import StackComponentFlavor, StackComponentType
from zenml.stack import StackComponent


class MockComponentFlavor(StackComponentFlavor):
    MOCK = "mock"


class MockComponent(StackComponent):
    name = "MockComponent"
    supports_local_execution = False
    supports_remote_execution = False
    some_public_attribute_name = "Aria"
    _some_private_attribute_name = "Also Aria"

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.ORCHESTRATOR

    @property
    def flavor(self) -> MockComponentFlavor:
        return MockComponentFlavor.MOCK


@pytest.fixture
def mock_component_class():
    return MockComponent
