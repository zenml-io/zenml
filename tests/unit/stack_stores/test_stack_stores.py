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
import shutil
from pathlib import Path

import pytest

from zenml.constants import LOCAL_CONFIG_DIRECTORY_NAME
from zenml.enums import StackComponentType, StorageType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack
from zenml.stack_stores import BaseStackStore, LocalStackStore, SqlStackStore
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper


def _stack_store_for_type(
    store_type: StorageType, path: Path
) -> BaseStackStore:
    if store_type == StorageType.YAML_STORAGE:
        return LocalStackStore(str(path))
    elif store_type == StorageType.SQLITE_STORAGE:
        return SqlStackStore(f"sqlite:///{path / 'store.db'}")
    else:
        raise NotImplementedError(f"No StackStore for {store_type}")


@pytest.mark.parametrize(
    "store_type", [StorageType.YAML_STORAGE, StorageType.SQLITE_STORAGE]
)
def test_register_deregister_stacks(
    tmp_path_factory: pytest.TempPathFactory, store_type: StorageType
):
    """Test creating a new stack store and adding default local stack."""
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_stack_store")
    os.mkdir(tmp_path / LOCAL_CONFIG_DIRECTORY_NAME)

    # stack store starts off empty
    stack_store = _stack_store_for_type(store_type, tmp_path)
    assert len(stack_store.stacks) == 0

    # add the default stack
    stack = Stack.default_local_stack()
    stack_store.register_stack(StackWrapper.from_stack(stack))
    assert len(stack_store.stacks) == 1
    assert len(stack_store.stack_configurations) == 1

    # retrieve the default stack
    got_stack = stack_store.get_stack(stack.name)
    assert got_stack.name == stack.name
    stack_configuration = stack_store.get_stack_configuration(stack.name)
    assert set(stack_configuration) == {
        "orchestrator",
        "metadata_store",
        "artifact_store",
    }
    assert (
        stack_configuration[StackComponentType.ORCHESTRATOR]
        == "local_orchestrator"
    )

    # can't register the same stack twice or another stack with the same name
    with pytest.raises(StackExistsError):
        stack_store.register_stack(StackWrapper.from_stack(stack))
    with pytest.raises(StackExistsError):
        stack_store.register_stack(StackWrapper(name=stack.name, components=[]))

    # remove the stack again
    stack_store.deregister_stack(stack.name)
    assert len(stack_store.stacks) == 0
    with pytest.raises(KeyError):
        _ = stack_store.get_stack(stack.name)

    # now can add another stack with the same name
    stack_store.register_stack(StackWrapper(name=stack.name, components=[]))
    assert len(stack_store.stacks) == 1

    # clean up the temp fixture (TODO: how to parametrize a fixture?)
    shutil.rmtree(tmp_path)


@pytest.mark.parametrize(
    "store_type", [StorageType.YAML_STORAGE, StorageType.SQLITE_STORAGE]
)
def test_register_deregister_components(
    tmp_path_factory: pytest.TempPathFactory, store_type: StorageType
):
    """Test adding and removing stack components."""
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_stack_store")
    os.mkdir(tmp_path / LOCAL_CONFIG_DIRECTORY_NAME)

    # stack store starts off empty
    stack_store = _stack_store_for_type(store_type, tmp_path)
    for component_type in StackComponentType:
        assert len(stack_store.get_stack_components(component_type)) == 0

    # add the default stack
    stack = Stack.default_local_stack()
    stack_store.register_stack(StackWrapper.from_stack(stack))

    required_components = {
        StackComponentType.ARTIFACT_STORE,
        StackComponentType.METADATA_STORE,
        StackComponentType.ORCHESTRATOR,
    }
    for component_type in StackComponentType:
        component_type = StackComponentType(component_type)
        if component_type in required_components:
            assert len(stack_store.get_stack_components(component_type)) == 1
        else:
            assert len(stack_store.get_stack_components(component_type)) == 0

    # get a component
    orchestrator = stack_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, "local_orchestrator"
    )
    assert orchestrator.flavor == "local"
    assert orchestrator.name == "local_orchestrator"

    # can't add another orchestrator of same name
    with pytest.raises(StackComponentExistsError):
        stack_store.register_stack_component(
            StackComponentWrapper.from_component(
                LocalOrchestrator(
                    name="local_orchestrator",
                )
            )
        )

    # but can add one if it has a different name
    stack_store.register_stack_component(
        StackComponentWrapper.from_component(
            LocalOrchestrator(
                name="local_orchestrator_part_2_the_remix",
            )
        )
    )
    assert (
        len(stack_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 2
    )

    # can't delete an orchestrator that's part of a stack
    with pytest.raises(ValueError):
        stack_store.deregister_stack_component(
            StackComponentType.ORCHESTRATOR, "local_orchestrator"
        )

    # but can if the stack is deleted first
    stack_store.deregister_stack("local_stack")
    stack_store.deregister_stack_component(
        StackComponentType.ORCHESTRATOR, "local_orchestrator"
    )
    assert (
        len(stack_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 1
    )
