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
import random
import shutil

import pytest

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import REPOSITORY_DIRECTORY_NAME
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError, EntityExistsError
from zenml.logger import get_logger
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack
from zenml.zen_service.zen_service import ZenService, ZenServiceConfig
from zenml.zen_stores import (
    BaseZenStore,
    LocalZenStore,
    RestZenStore,
    SqlZenStore,
)
from zenml.zen_stores.models import StackComponentWrapper, StackWrapper

logger = get_logger(__name__)

not_windows = platform.system() != "Windows"
store_types = [StoreType.LOCAL, StoreType.SQL] + [StoreType.REST] * not_windows


@pytest.fixture(
    params=store_types
)
def fresh_zen_store(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> BaseZenStore:
    store_type = request.param
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_zen_store")
    os.mkdir(tmp_path / REPOSITORY_DIRECTORY_NAME)

    if store_type == StoreType.LOCAL:
        yield LocalZenStore().initialize(str(tmp_path))
    elif store_type == StoreType.SQL:
        yield SqlZenStore().initialize(f"sqlite:///{tmp_path / 'store.db'}")
    elif store_type == StoreType.REST:
        port = random.randint(8003, 9000)
        # create temporary zen store and profile configuration for unit tests
        backing_zen_store = LocalZenStore().initialize(str(tmp_path))
        store_profile = ProfileConfiguration(
            name=f"test_profile_{hash(str(tmp_path))}",
            store_url=backing_zen_store.url,
            store_type=backing_zen_store.type,
        )

        zen_service = ZenService(
            ZenServiceConfig(
                port=port,
                store_profile_configuration=store_profile,
            )
        )
        zen_service.start(timeout=10)
        # rest zen store can't have trailing slash on url
        url = zen_service.zen_service_uri.strip("/")
        yield RestZenStore().initialize(url)
        zen_service.stop()
    else:
        raise NotImplementedError(f"No ZenStore for {store_type}")

    shutil.rmtree(tmp_path)


def test_register_deregister_stacks(fresh_zen_store):
    """Test creating a new zen store."""
    stack = Stack.default_local_stack()

    # zen store is pre-initialized with the default stack
    zen_store = fresh_zen_store
    assert len(zen_store.stacks) == 1
    assert len(zen_store.stack_configurations) == 1

    # retrieve the default stack
    got_stack = zen_store.get_stack(stack.name)
    assert got_stack.name == stack.name
    stack_configuration = zen_store.get_stack_configuration(stack.name)
    assert set(stack_configuration) == {
        "orchestrator",
        "metadata_store",
        "artifact_store",
    }
    assert stack_configuration[StackComponentType.ORCHESTRATOR] == "default"

    # can't register the same stack twice or another stack with the same name
    with pytest.raises(StackExistsError):
        zen_store.register_stack(StackWrapper.from_stack(stack))
    with pytest.raises(StackExistsError):
        zen_store.register_stack(StackWrapper(name=stack.name, components=[]))

    # can't remove a stack that doesn't exist:
    with pytest.raises(KeyError):
        zen_store.deregister_stack("overflow")

    # remove the default stack
    zen_store.deregister_stack(stack.name)
    assert len(zen_store.stacks) == 0
    with pytest.raises(KeyError):
        _ = zen_store.get_stack(stack.name)

    # now can add another stack with the same name
    zen_store.register_stack(StackWrapper(name=stack.name, components=[]))
    assert len(zen_store.stacks) == 1


def test_register_deregister_components(fresh_zen_store):
    """Test adding and removing stack components."""
    required_components = {
        StackComponentType.ARTIFACT_STORE,
        StackComponentType.METADATA_STORE,
        StackComponentType.ORCHESTRATOR,
    }

    # zem store starts off with the default stack
    zen_store = fresh_zen_store
    for component_type in StackComponentType:
        component_type = StackComponentType(component_type)
        if component_type in required_components:
            assert len(zen_store.get_stack_components(component_type)) == 1
        else:
            assert len(zen_store.get_stack_components(component_type)) == 0

    # get a component
    orchestrator = zen_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )

    assert orchestrator.flavor == "local"
    assert orchestrator.name == "default"

    # can't add another orchestrator of same name
    with pytest.raises(StackComponentExistsError):
        zen_store.register_stack_component(
            StackComponentWrapper.from_component(
                LocalOrchestrator(
                    name="default",
                )
            )
        )

    # but can add one if it has a different name
    zen_store.register_stack_component(
        StackComponentWrapper.from_component(
            LocalOrchestrator(
                name="local_orchestrator_part_2_the_remix",
            )
        )
    )
    assert (
        len(zen_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 2
    )

    # can't delete an orchestrator that's part of a stack
    with pytest.raises(ValueError):
        zen_store.deregister_stack_component(
            StackComponentType.ORCHESTRATOR, "default"
        )

    # but can if the stack is deleted first
    zen_store.deregister_stack("default")
    zen_store.deregister_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )
    assert (
        len(zen_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 1
    )


def test_user_management(fresh_zen_store):
    """Tests user creation and deletion."""
    # starts with a default user
    assert len(fresh_zen_store.users) == 1

    fresh_zen_store.create_user("aria")
    assert len(fresh_zen_store.users) == 2

    with pytest.raises(EntityExistsError):
        # usernames need to be unique
        fresh_zen_store.create_user("aria")

    fresh_zen_store.create_team("team_aria")
    fresh_zen_store.add_user_to_team(team_name="team_aria", user_name="aria")

    fresh_zen_store.create_role("cat")
    fresh_zen_store.assign_role(
        role_name="cat", entity_name="aria", is_user=True
    )

    assert len(fresh_zen_store.get_users_for_team("team_aria")) == 1
    assert len(fresh_zen_store.role_assignments) == 1

    # Deletes the user as well as any team/role assignment
    fresh_zen_store.delete_user("aria")
    assert len(fresh_zen_store.users) == 1
    assert len(fresh_zen_store.get_users_for_team("team_aria")) == 0
    assert len(fresh_zen_store.role_assignments) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent user
        fresh_zen_store.delete_user("aria")


def test_team_management(fresh_zen_store):
    """Tests team creation and deletion."""
    fresh_zen_store.create_user("adam")
    fresh_zen_store.create_user("hamza")
    fresh_zen_store.create_team("zenml")

    fresh_zen_store.add_user_to_team(team_name="zenml", user_name="adam")
    fresh_zen_store.add_user_to_team(team_name="zenml", user_name="hamza")
    assert len(fresh_zen_store.get_users_for_team("zenml")) == 2

    with pytest.raises(Exception):
        # non-existent team
        fresh_zen_store.add_user_to_team(team_name="airflow", user_name="hamza")

    with pytest.raises(Exception):
        # non-existent user
        fresh_zen_store.add_user_to_team(team_name="zenml", user_name="elon")

    fresh_zen_store.remove_user_from_team(team_name="zenml", user_name="hamza")
    assert len(fresh_zen_store.get_users_for_team("zenml")) == 1

    fresh_zen_store.delete_team("zenml")
    assert len(fresh_zen_store.get_teams_for_user("adam")) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent team
        fresh_zen_store.delete_team("zenml")


def test_project_management(fresh_zen_store):
    """Tests project creation and deletion."""
    fresh_zen_store.create_project("secret_project")
    assert len(fresh_zen_store.projects) == 1
    fresh_zen_store.delete_project("secret_project")
    assert len(fresh_zen_store.projects) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent project
        fresh_zen_store.delete_project("secret_project")


def test_role_management(fresh_zen_store):
    """Tests role creation, deletion, assignment and revocation."""
    fresh_zen_store.create_user("aria")
    fresh_zen_store.create_team("cats")
    fresh_zen_store.add_user_to_team(user_name="aria", team_name="cats")
    fresh_zen_store.create_role("beautiful")
    assert len(fresh_zen_store.roles) == 1

    fresh_zen_store.assign_role(
        role_name="beautiful", entity_name="aria", is_user=True
    )

    assert (
        len(fresh_zen_store.get_role_assignments_for_user(user_name="aria"))
        == 1
    )

    fresh_zen_store.assign_role(
        role_name="beautiful", entity_name="cats", is_user=False
    )

    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=False
            )
        )
        == 1
    )
    assert (
        len(fresh_zen_store.get_role_assignments_for_team(team_name="cats"))
        == 1
    )
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=True
            )
        )
        == 2
    )

    fresh_zen_store.revoke_role(
        role_name="beautiful", entity_name="aria", is_user=True
    )
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=False
            )
        )
        == 0
    )

    fresh_zen_store.delete_team("cats")
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=True
            )
        )
        == 0
    )
