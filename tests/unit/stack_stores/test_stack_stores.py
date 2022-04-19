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
import base64
import os
import platform
import random
import shutil
from contextlib import ExitStack as does_not_raise

import pytest
import yaml

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import REPOSITORY_DIRECTORY_NAME
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.orchestrators import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)
from zenml.services import ServiceState
from zenml.stack import Stack
from zenml.stack.stack_component import StackComponent
from zenml.stack.stack_component_class_registry import (
    StackComponentClassRegistry,
)
from zenml.stack_stores import (
    BaseStackStore,
    LocalStackStore,
    RestStackStore,
    SqlStackStore,
)
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper
from zenml.zen_service.zen_service import ZenService, ZenServiceConfig

logger = get_logger(__name__)


not_windows = platform.system() != "Windows"
store_types = [StoreType.LOCAL, StoreType.SQL] + [StoreType.REST] * not_windows


@pytest.fixture(params=store_types)
def fresh_stack_store(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> BaseStackStore:
    store_type = request.param
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_stack_store")
    os.mkdir(tmp_path / REPOSITORY_DIRECTORY_NAME)

    if store_type == StoreType.LOCAL:
        yield LocalStackStore().initialize(str(tmp_path))
    elif store_type == StoreType.SQL:
        yield SqlStackStore().initialize(f"sqlite:///{tmp_path / 'store.db'}")
    elif store_type == StoreType.REST:
        port = random.randint(8003, 9000)
        # create temporary stack store and profile configuration for unit tests
        backing_stack_store = LocalStackStore().initialize(str(tmp_path))
        store_profile = ProfileConfiguration(
            name=f"test_profile_{hash(str(tmp_path))}",
            store_url=backing_stack_store.url,
            store_type=backing_stack_store.type,
        )

        zen_service = ZenService(
            ZenServiceConfig(
                port=port,
                store_profile_configuration=store_profile,
            )
        )
        zen_service.start(timeout=10)
        # rest stack store can't have trailing slash on url
        url = zen_service.zen_service_uri.strip("/")
        yield RestStackStore().initialize(url)
        zen_service.stop(timeout=10)
        assert zen_service.check_status()[0] == ServiceState.INACTIVE
    else:
        raise NotImplementedError(f"No StackStore for {store_type}")

    shutil.rmtree(tmp_path)


def test_register_deregister_stacks(fresh_stack_store: BaseStackStore):
    """Test creating a new stack store."""

    stack = Stack.default_local_stack()

    # stack store is pre-initialized with the default stack
    stack_store = fresh_stack_store
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
    assert stack_configuration[StackComponentType.ORCHESTRATOR] == "default"

    # can't register the same stack twice or another stack with the same name
    with pytest.raises(StackExistsError):
        stack_store.register_stack(StackWrapper.from_stack(stack))
    with pytest.raises(StackExistsError):
        stack_store.register_stack(StackWrapper(name=stack.name, components=[]))

    # can't remove a stack that doesn't exist:
    with pytest.raises(KeyError):
        stack_store.deregister_stack("overflow")

    # remove the default stack
    stack_store.deregister_stack(stack.name)
    assert len(stack_store.stacks) == 0
    with pytest.raises(KeyError):
        _ = stack_store.get_stack(stack.name)

    # now can add another stack with the same name
    stack_store.register_stack(StackWrapper(name=stack.name, components=[]))
    assert len(stack_store.stacks) == 1


def test_register_deregister_components(fresh_stack_store: BaseStackStore):
    """Test adding and removing stack components."""

    required_components = {
        StackComponentType.ARTIFACT_STORE,
        StackComponentType.METADATA_STORE,
        StackComponentType.ORCHESTRATOR,
    }

    # stack store starts off with the default stack
    stack_store = fresh_stack_store
    for component_type in StackComponentType:
        component_type = StackComponentType(component_type)
        if component_type in required_components:
            assert len(stack_store.get_stack_components(component_type)) == 1
        else:
            assert len(stack_store.get_stack_components(component_type)) == 0

    # get a component
    orchestrator = stack_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )

    assert orchestrator.flavor == "local"
    assert orchestrator.name == "default"

    # can't add another orchestrator of same name
    with pytest.raises(StackComponentExistsError):
        stack_store.register_stack_component(
            StackComponentWrapper.from_component(
                LocalOrchestrator(
                    name="default",
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
            StackComponentType.ORCHESTRATOR, "default"
        )

    # but can if the stack is deleted first
    stack_store.deregister_stack("default")
    stack_store.deregister_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )
    assert (
        len(stack_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 1
    )


def get_component_from_wrapper(
    wrapper: StackComponentWrapper,
) -> StackComponent:
    """Instantiate a StackComponent from the Configuration."""
    component_class = StackComponentClassRegistry.get_class(
        component_type=wrapper.type, component_flavor=wrapper.flavor
    )
    component_config = yaml.safe_load(base64.b64decode(wrapper.config).decode())
    return component_class.parse_obj(component_config)


def test_update_stack_with_new_component(fresh_stack_store: BaseStackStore):
    """Test updating a stack with a new component"""
    current_stack_store = fresh_stack_store

    new_orchestrator = LocalOrchestrator(name="new_orchestrator")

    updated_stack = Stack(
        name="default",
        orchestrator=new_orchestrator,
        metadata_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
    )

    with does_not_raise():
        current_stack_store.update_stack(StackWrapper.from_stack(updated_stack))

    assert (
        len(
            current_stack_store.get_stack_components(
                StackComponentType.ORCHESTRATOR
            )
        )
        == 2
    )
    assert new_orchestrator in [
        get_component_from_wrapper(component)
        for component in current_stack_store.get_stack_components(
            StackComponentType.ORCHESTRATOR
        )
    ]
    assert new_orchestrator in [
        get_component_from_wrapper(component)
        for component in current_stack_store.get_stack("default").components
    ]


def test_update_stack_when_component_not_part_of_stack(
    fresh_stack_store: BaseStackStore,
):
    """Test adding a new component as part of an existing stack."""
    current_stack_store = fresh_stack_store

    local_secrets_manager = LocalSecretsManager(name="local_secrets_manager")

    updated_stack = Stack(
        name="default",
        orchestrator=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.ORCHESTRATOR, "default"
            )
        ),
        metadata_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
        secrets_manager=local_secrets_manager,
    )

    with does_not_raise():
        current_stack_store.update_stack(StackWrapper.from_stack(updated_stack))

    assert (
        len(
            current_stack_store.get_stack_components(
                StackComponentType.SECRETS_MANAGER
            )
        )
        == 1
    )
    assert local_secrets_manager in [
        get_component_from_wrapper(component)
        for component in current_stack_store.get_stack_components(
            StackComponentType.SECRETS_MANAGER
        )
    ]
    assert local_secrets_manager in [
        get_component_from_wrapper(component)
        for component in current_stack_store.get_stack("default").components
    ]


def test_update_non_existent_stack_raises_error(
    fresh_stack_store: BaseStackStore,
):
    """Test updating a non-existent stack raises an error."""
    current_stack_store = fresh_stack_store

    stack = Stack(
        name="aria_is_a_cat_not_a_stack",
        orchestrator=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.ORCHESTRATOR, "default"
            )
        ),
        metadata_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            current_stack_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
    )

    with pytest.raises(DoesNotExistException):
        current_stack_store.update_stack(StackWrapper.from_stack(stack))
