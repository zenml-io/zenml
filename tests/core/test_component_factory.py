#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pytest

from zenml.core.component_factory import (
    ComponentFactory,
    artifact_store_factory,
    metadata_store_factory,
    orchestrator_store_factory,
)

COMPONENT_FACTORIES = [
    artifact_store_factory,
    metadata_store_factory,
    orchestrator_store_factory,
]


@pytest.mark.parametrize("component_factory", COMPONENT_FACTORIES)
def test_factories_are_type_component_factory(component_factory):
    assert isinstance(component_factory, ComponentFactory)
    assert component_factory.name is not None
    assert isinstance(component_factory.name, str)
    assert isinstance(component_factory.components, dict)
