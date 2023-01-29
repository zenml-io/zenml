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
import uuid
from contextlib import ExitStack as does_not_raise
from typing import Callable, Type, TypeVar

import pytest
from pydantic import BaseModel

from tests.integration.functional.zen_stores.utils import sample_name
from zenml.client import Client
from zenml.constants import DEFAULT_STACK
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import (
    BaseFilterModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentUpdateModel,
    ProjectFilterModel,
    ProjectRequestModel,
    ProjectUpdateModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleUpdateModel,
    TeamFilterModel,
    TeamRequestModel,
    TeamRoleAssignmentRequestModel,
    TeamUpdateModel,
    UserFilterModel,
    UserRequestModel,
    UserRoleAssignmentRequestModel,
    UserUpdateModel, StackUpdateModel,
)
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    ProjectScopedRequestModel,
)
from zenml.models.page_model import Page
from zenml.zen_stores.base_zen_store import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_GUEST_ROLE,
    DEFAULT_PROJECT_NAME,
    DEFAULT_USERNAME, DEFAULT_STACK_NAME,
)

DEFAULT_NAME = "default"

# .------------.
# | BASIC CRUD |
# '------------'

AnyRequestModel = TypeVar("AnyRequestModel", bound=BaseRequestModel)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


class CrudTestConfig(BaseModel):
    """Model to collect all methods pertaining to a given entity.

    Please Note: This implementation will only work for named entities,
    (entities with a `name` field)
    """

    zen_store_list_method: str
    zen_store_get_method: str
    zen_store_create_method: str
    zen_store_update_method: str
    zen_store_delete_method: str
    create_model: "BaseRequestModel"
    update_model: "BaseRequestModel"
    filter_model: Type[BaseFilterModel]
    entity_name: str

    @property
    def list_method(
        self,
    ) -> Callable[[BaseFilterModel], Page[AnyResponseModel]]:
        store = Client().zen_store
        return getattr(store, self.zen_store_list_method)

    @property
    def get_method(self) -> Callable[[uuid.UUID], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, self.zen_store_get_method)

    @property
    def delete_method(self) -> Callable[[uuid.UUID], None]:
        store = Client().zen_store
        return getattr(store, self.zen_store_delete_method)

    @property
    def create_method(self) -> Callable[[AnyRequestModel], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, self.zen_store_create_method)

    @property
    def update_method(
        self,
    ) -> Callable[[uuid.UUID, AnyRequestModel], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, self.zen_store_update_method)


project_crud_test_config = CrudTestConfig(
    zen_store_list_method="list_projects",
    zen_store_get_method="get_project",
    zen_store_create_method="create_project",
    zen_store_update_method="update_project",
    zen_store_delete_method="delete_project",
    create_model=ProjectRequestModel(name=sample_name("sample_project")),
    update_model=ProjectUpdateModel(
        name=sample_name("updated_sample_project")
    ),
    filter_model=ProjectFilterModel,
    entity_name="project",
)


user_crud_test_config = CrudTestConfig(
    zen_store_list_method="list_users",
    zen_store_get_method="get_user",
    zen_store_create_method="create_user",
    zen_store_update_method="update_user",
    zen_store_delete_method="delete_user",
    create_model=UserRequestModel(name=sample_name("sample_user")),
    update_model=UserUpdateModel(name=sample_name("updated_sample_user")),
    filter_model=UserFilterModel,
    entity_name="user",
)


role_crud_test_config = CrudTestConfig(
    zen_store_list_method="list_roles",
    zen_store_get_method="get_role",
    zen_store_create_method="create_role",
    zen_store_update_method="update_role",
    zen_store_delete_method="delete_role",
    create_model=RoleRequestModel(
        name=sample_name("sample_role"), permissions=set()
    ),
    update_model=RoleUpdateModel(name=sample_name("updated_sample_role")),
    filter_model=RoleFilterModel,
    entity_name="role",
)

team_crud_test_config = CrudTestConfig(
    zen_store_list_method="list_teams",
    zen_store_get_method="get_team",
    zen_store_create_method="create_team",
    zen_store_update_method="update_team",
    zen_store_delete_method="delete_team",
    create_model=TeamRequestModel(name=sample_name("sample_team")),
    update_model=TeamUpdateModel(name=sample_name("updated_sample_team")),
    filter_model=TeamFilterModel,
    entity_name="team",
)

component_crud_test_config = CrudTestConfig(
    zen_store_list_method="list_stack_components",
    zen_store_get_method="get_stack_component",
    zen_store_create_method="create_stack_component",
    zen_store_update_method="update_stack_component",
    zen_store_delete_method="delete_stack_component",
    create_model=ComponentRequestModel(
        name=sample_name("sample_component"),
        type=StackComponentType.ORCHESTRATOR,
        flavor="local",
        configuration={},
        user=uuid.uuid4(),
        project=uuid.uuid4(),
    ),
    update_model=ComponentUpdateModel(
        name=sample_name("updated_sample_component")
    ),
    filter_model=ComponentFilterModel,
    entity_name="component",
)

list_of_entities = [
    project_crud_test_config,
    user_crud_test_config,
    role_crud_test_config,
    team_crud_test_config,
    component_crud_test_config,
]


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_basic_crud_for_entity(crud_test_config: CrudTestConfig):
    """Tests the basic crud operations for a given entity."""
    client = Client()

    # Create the entity
    create_model = crud_test_config.create_model
    if isinstance(create_model, ProjectScopedRequestModel):
        create_model.user = client.active_user.id
        create_model.project = client.active_project.id
    # This generic test only works for entities with a name field
    assert create_model.name
    # Test the creation
    created_entity = crud_test_config.create_method(create_model)
    # Filter by name to verify the entity was actually created
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(name=create_model.name)
    )
    assert entities_list.total > 0
    # Filter by id to verify the entity was actually created
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(id=created_entity.id)
    )
    assert entities_list.total > 0
    # Test the get method
    with does_not_raise():
        returned_entity_by_id = crud_test_config.get_method(created_entity.id)
    assert returned_entity_by_id == created_entity
    # Update the created entity
    update_model = crud_test_config.update_model
    assert update_model.name
    with does_not_raise():
        updated_entity = crud_test_config.update_method(
            created_entity.id, update_model
        )
    assert updated_entity.id == created_entity.id
    # Verify the entity can be found using the new name, not the old name
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(name=update_model.name)
    )
    assert entities_list.total > 0
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(name=create_model.name)
    )
    assert entities_list.total == 0
    # Cleanup
    with does_not_raise():
        crud_test_config.delete_method(created_entity.id)
    # Filter by name to verify the entity was actually deleted
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(name=update_model.name)
    )
    assert entities_list.total == 0
    # Filter by id to verify the entity was actually deleted
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(id=created_entity.id)
    )
    assert entities_list.total == 0


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_create_entity_twice_fails(crud_test_config: CrudTestConfig):
    """Tests getting a non-existent entity by id."""
    client = Client()
    # Create the entity
    create_model = crud_test_config.create_model
    if isinstance(create_model, ProjectScopedRequestModel):
        create_model.user = client.active_user.id
        create_model.project = client.active_project.id
    # First creation is successful
    created_entity = crud_test_config.create_method(
        crud_test_config.create_model
    )
    # Second one fails
    with pytest.raises(EntityExistsError):
        crud_test_config.create_method(crud_test_config.create_model)
    # Cleanup
    with does_not_raise():
        crud_test_config.delete_method(created_entity.id)
    # Filter by id to verify the entity was actually deleted
    entities_list = crud_test_config.list_method(
        crud_test_config.filter_model(id=created_entity.id)
    )
    assert entities_list.total == 0


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_get_nonexistent_entity_fails(crud_test_config: CrudTestConfig):
    """Tests getting a non-existent entity by id."""
    with pytest.raises(KeyError):
        crud_test_config.get_method(uuid.uuid4())


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_updating_nonexisting_entity_raises_error(
    crud_test_config: CrudTestConfig,
):
    """Tests updating a nonexistent entity raises an error."""
    # Update the created entity
    update_model = crud_test_config.update_model
    assert update_model.name
    with pytest.raises(KeyError):
        crud_test_config.update_method(uuid.uuid4(), update_model)


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_deleting_nonexistent_project_raises_error(
    crud_test_config: CrudTestConfig,
):
    """Tests deleting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        crud_test_config.delete_method(uuid.uuid4())


# .----------.
# | PROJECTS |
# '----------'


def test_only_one_default_project_present():
    """Tests that one and only one default project is present."""
    client = Client()
    assert (
        len(client.zen_store.list_projects(ProjectFilterModel(name="default")))
        == 1
    )


def test_updating_default_project_fails():
    """Tests updating the default project."""
    client = Client()

    default_project = client.zen_store.get_project(DEFAULT_PROJECT_NAME)
    assert default_project.name == DEFAULT_PROJECT_NAME
    project_update = ProjectUpdateModel(
        name="aria_project",
        description="Aria has taken possession of this project.",
    )
    with pytest.raises(IllegalOperationError):
        client.zen_store.update_project(
            project_id=default_project.id, project_update=project_update
        )


def test_deleting_default_project_fails():
    """Tests deleting the default project."""
    client = Client()
    with pytest.raises(IllegalOperationError):
        client.zen_store.delete_project(DEFAULT_NAME)


# .-------.
# | TEAMS |
# '-------'


def test_adding_user_to_team():
    """Tests adding a user to a team."""
    zen_store = Client().zen_store
    user_name = "aria"
    team_name = "arias_team"
    try:
        new_user = UserRequestModel(name=user_name)
        new_user = zen_store.create_user(new_user)
        new_team = TeamRequestModel(name=team_name)
        new_team = zen_store.create_team(new_team)

        team_update = TeamUpdateModel(users=[new_user.id])
        team_update = zen_store.update_team(
            team_id=new_team.id, team_update=team_update
        )

        assert new_user.id in team_update.user_ids
        assert len(team_update.users) == 1

        # Make sure the team name has not been inadvertently changed
        assert zen_store.get_team(new_team.id).name == team_name
    # Cleanup no matter what
    finally:
        try:
            user = zen_store.get_user(user_name_or_id=user_name)
        except KeyError:
            pass
        else:
            zen_store.delete_user(user.id)
        try:
            team = zen_store.get_team(team_name_or_id=team_name)
        except KeyError:
            pass
        else:
            zen_store.delete_team(team.id)


def test_adding_nonexistent_user_to_real_team_raises_error():
    """Tests adding a nonexistent user to a team raises an error."""
    zen_store = Client().zen_store
    team_name = "arias_team"
    try:
        new_team = TeamRequestModel(name=team_name)
        new_team = zen_store.create_team(new_team)

        nonexistent_id = uuid.uuid4()

        team_update = TeamUpdateModel(users=[nonexistent_id])
        with pytest.raises(KeyError):
            team_update = zen_store.update_team(
                team_id=new_team.id, team_update=team_update
            )
    # Cleanup no matter what
    finally:
        try:
            team = zen_store.get_team(team_name_or_id=team_name)
        except KeyError:
            pass
        else:
            zen_store.delete_team(team.id)


def test_removing_user_from_team_succeeds():
    """Tests removing a user from a team."""

    zen_store = Client().zen_store
    user_name = sample_name("aria")
    team_name = sample_name("arias_team")
    try:
        new_user = UserRequestModel(name=user_name)
        new_user = zen_store.create_user(new_user)
        new_team = TeamRequestModel(name=team_name, users=[new_user.id])
        new_team = zen_store.create_team(new_team)
        assert new_user.id in new_team.user_ids

        team_update = TeamUpdateModel(users=[])
        team_update = zen_store.update_team(
            team_id=new_team.id, team_update=team_update
        )

        assert new_user.id not in team_update.user_ids
    # Cleanup no matter what
    finally:
        try:
            user = zen_store.get_user(user_name_or_id=user_name)
        except KeyError:
            pass
        else:
            zen_store.delete_user(user.id)
        try:
            team = zen_store.get_team(team_name_or_id=team_name)
        except KeyError:
            pass
        else:
            zen_store.delete_team(team.id)


#  .------.
# | USERS |
# '-------'


def test_active_user():
    """Tests the active user can be queried with .get_user()."""
    zen_store = Client().zen_store
    active_user = zen_store.get_user()
    assert active_user is not None
    # The SQL zen_store only supports the default user as active user
    if zen_store.type == StoreType.SQL:
        assert active_user.name == DEFAULT_USERNAME
    else:
        # TODO: Implement this
        assert True


def test_updating_default_user_fails():
    """Tests that updating the default user is prohibited."""
    client = Client()
    default_user = client.zen_store.get_user(DEFAULT_USERNAME)
    assert default_user
    user_update = UserUpdateModel(name="axl")
    with pytest.raises(IllegalOperationError):
        client.zen_store.update_user(
            user_id=default_user.id, user_update=user_update
        )


def test_deleting_default_user_fails():
    """Tests that deleting the default user is prohibited."""
    zen_store = Client().zen_store
    with pytest.raises(IllegalOperationError):
        zen_store.delete_user("default")


#  .------.
# | ROLES |
# '-------'


def test_creating_role_with_empty_permissions_succeeds():
    """Tests creating a role."""
    zen_store = Client().zen_store
    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)
    with does_not_raise():
        zen_store.get_role(role_name_or_id=new_role.name)
    list_of_roles = zen_store.list_roles(RoleFilterModel(name=new_role.name))
    assert list_of_roles.total > 0
    # Cleanup
    with does_not_raise():
        zen_store.delete_role(created_role.id)


def test_deleting_builtin_role_fails():
    """Tests deleting a built-in role fails."""
    zen_store = Client().zen_store

    with pytest.raises(IllegalOperationError):
        zen_store.delete_role(DEFAULT_ADMIN_ROLE)

    with pytest.raises(IllegalOperationError):
        zen_store.delete_role(DEFAULT_GUEST_ROLE)


def test_updating_builtin_role_fails():
    """Tests updating a built-in role fails."""
    zen_store = Client().zen_store

    role = zen_store.get_role(DEFAULT_ADMIN_ROLE)
    role_update = RoleUpdateModel(name="cat_feeder")

    with pytest.raises(IllegalOperationError):
        zen_store.update_role(role_id=role.id, role_update=role_update)

    role = zen_store.get_role(DEFAULT_GUEST_ROLE)
    with pytest.raises(IllegalOperationError):
        zen_store.update_role(role_id=role.id, role_update=role_update)


def test_deleting_assigned_role_fails():
    """Tests assigning a role to a user."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_user = UserRequestModel(name=sample_name("aria"))
    created_user = zen_store.create_user(new_user)

    role_assignment = UserRoleAssignmentRequestModel(
        role=created_role.id,
        user=created_user.id,
        project=None,
    )
    with does_not_raise():
        (zen_store.create_user_role_assignment(role_assignment))
    with pytest.raises(IllegalOperationError):
        zen_store.delete_role(created_role.id)

    # Cleanup
    with does_not_raise():
        # By deleting the user first, the role assignment is cleaned up as well
        zen_store.delete_user(created_user.id)
        zen_store.delete_role(created_role.id)


#  .----------------
# | ROLE ASSIGNMENTS
# '-----------------


def test_assigning_role_to_user_succeeds():
    """Tests assigning a role to a user."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_user = UserRequestModel(name=sample_name("aria"))
    created_user = zen_store.create_user(new_user)

    role_assignment = UserRoleAssignmentRequestModel(
        role=created_role.id,
        user=created_user.id,
        project=None,
    )
    with does_not_raise():
        (zen_store.create_user_role_assignment(role_assignment))
    # Cleanup
    with does_not_raise():
        zen_store.delete_user(created_user.id)
        zen_store.delete_role(created_role.id)


def test_assigning_role_to_team_succeeds():
    """Tests assigning a role to a user."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_team = TeamRequestModel(name=sample_name("cats"))
    created_team = zen_store.create_team(new_team)

    role_assignment = TeamRoleAssignmentRequestModel(
        role=created_role.id,
        team=created_team.id,
        project=None,
    )
    with does_not_raise():
        (zen_store.create_team_role_assignment(role_assignment))
    # Cleanup
    with does_not_raise():
        zen_store.delete_team(created_team.id)
        zen_store.delete_role(created_role.id)


def test_assigning_role_if_assignment_already_exists_fails():
    """Tests assigning a role to a user if the assignment already exists."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_user = UserRequestModel(name=sample_name("aria"))
    created_user = zen_store.create_user(new_user)

    role_assignment = UserRoleAssignmentRequestModel(
        role=created_role.id,
        user=created_user.id,
        project=None,
    )
    with does_not_raise():
        (zen_store.create_user_role_assignment(role_assignment))
    with pytest.raises(EntityExistsError):
        (zen_store.create_user_role_assignment(role_assignment))

    # Cleanup
    with does_not_raise():
        zen_store.delete_user(created_user.id)
        zen_store.delete_role(created_role.id)


def test_revoking_role_for_user_succeeds():
    """Tests revoking a role for a user."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_user = UserRequestModel(name=sample_name("aria"))
    created_user = zen_store.create_user(new_user)

    role_assignment = UserRoleAssignmentRequestModel(
        role=created_role.id,
        user=created_user.id,
        project=None,
    )
    with does_not_raise():
        role_assignment = zen_store.create_user_role_assignment(
            role_assignment
        )
        zen_store.delete_user_role_assignment(
            user_role_assignment_id=role_assignment.id
        )
    with pytest.raises(KeyError):
        zen_store.get_user_role_assignment(
            user_role_assignment_id=role_assignment.id
        )

    # Cleanup
    with does_not_raise():
        zen_store.delete_user(created_user.id)
        zen_store.delete_role(created_role.id)


def test_revoking_role_for_team_succeeds():
    """Tests revoking a role for a team."""
    zen_store = Client().zen_store

    new_role = RoleRequestModel(name=sample_name("cat"), permissions=set())
    created_role = zen_store.create_role(new_role)

    new_team = TeamRequestModel(name=sample_name("cats"))
    created_team = zen_store.create_team(new_team)

    role_assignment = TeamRoleAssignmentRequestModel(
        role=created_role.id,
        team=created_team.id,
        project=None,
    )
    with does_not_raise():
        role_assignment = zen_store.create_team_role_assignment(
            role_assignment
        )
        zen_store.delete_team_role_assignment(
            team_role_assignment_id=role_assignment.id
        )
    with pytest.raises(KeyError):
        zen_store.get_team_role_assignment(
            team_role_assignment_id=role_assignment.id
        )

    # Cleanup
    with does_not_raise():
        zen_store.delete_team(created_team.id)
        zen_store.delete_role(created_role.id)


def test_revoking_nonexistent_role_fails():
    """Tests revoking a nonexistent role fails."""
    zen_store = Client().zen_store
    with pytest.raises(KeyError):
        zen_store.delete_team_role_assignment(
            team_role_assignment_id=uuid.uuid4()
        )
    with pytest.raises(KeyError):
        zen_store.delete_user_role_assignment(
            user_role_assignment_id=uuid.uuid4()
        )


#  .-------.
# | STACKS |
# '--------'


def test_updating_default_stack_fails():
    """Tests that updating the default stack is prohibited."""
    client = Client()

    default_stack = client.get_stack(DEFAULT_STACK_NAME)
    assert default_stack.name == DEFAULT_PROJECT_NAME
    stack_update = StackUpdateModel(name="axls_stack")
    with pytest.raises(IllegalOperationError):
        client.zen_store.update_stack(
             stack_id=default_stack.id, stack_update=stack_update
         )


def test_deleting_default_stack_fails():
    """Tests that deleting the default stack is prohibited."""
    client = Client()

    default_stack = client.get_stack(DEFAULT_STACK_NAME)
    with pytest.raises(IllegalOperationError):
        client.zen_store.delete_stack(default_stack.id)


# def test_list_stacks_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stacks."""
#     assert len(sql_store["store"].list_stacks()) == 1
#
#
# def test_list_stacks_fails_with_nonexistent_project(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stacks fails with nonexistent project."""
#     with pytest.raises(KeyError):
#         sql_store["store"].list_stacks(project_name_or_id=uuid.uuid4())
#
#
# def test_get_stack_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack."""
#     current_stack_id = sql_store["store"].list_stacks()[0].id
#     stack = sql_store["store"].get_stack(stack_id=current_stack_id)
#     assert stack is not None
#
#
# def test_get_stack_fails_with_nonexistent_stack_id(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack fails with nonexistent stack id."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack(uuid.uuid4())
#
#
# def test_register_stack_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests registering stack."""
#     new_stack = StackRequestModel(
#         name="arias_stack",
#         components={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     # TODO: [server] inject user and project into stack as well
#     sql_store["store"].create_stack(
#         stack=new_stack,
#     )
#     stacks = sql_store["store"].list_stacks(DEFAULT_NAME)
#     assert len(stacks) == 2
#     assert sql_store["store"].get_stack(stacks[0].id) is not None
#
#
# def test_register_stack_fails_when_stack_exists(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests registering stack fails when stack exists."""
#     new_stack = StackRequestModel(
#         name=DEFAULT_NAME,
#         components={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with pytest.raises(StackExistsError):
#         # TODO: [server] inject user and project into stack as well
#         sql_store["store"].create_stack(
#             stack=new_stack,
#         )
#
#
# def test_updating_stack_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating stack."""
#     new_stack = StackRequestModel(
#         name="arias_stack",
#         description="Aria likes her stacks.",
#         components={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     new_stack = sql_store["store"].create_stack(
#         stack=new_stack,
#     )
#     new_stack_name = "axls_stack"
#     stack_update = StackUpdateModel(name=new_stack_name)
#     sql_store["store"].update_stack(
#         stack_id=new_stack.id, stack_update=stack_update
#     )
#     assert sql_store["store"].get_stack(new_stack.id) is not None
#     assert sql_store["store"].get_stack(new_stack.id).name == new_stack_name
#     # Ensure unset fields of the `UpdateModel` are not changed
#     assert (
#         sql_store["store"].get_stack(new_stack.id).description
#         == new_stack.description
#     )
#
#
#
# def test_updating_nonexistent_stack_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating nonexistent stack fails."""
#     current_stack_id = sql_store["default_stack"].id
#     new_stack_name = "axls_stack"
#     stack_update = StackUpdateModel(name=new_stack_name)
#     nonexistent_id = uuid.uuid4()
#     with pytest.raises(KeyError):
#         sql_store["store"].update_stack(
#             stack_id=nonexistent_id, stack_update=stack_update
#         )
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack(nonexistent_id)
#     assert sql_store["store"].get_stack(current_stack_id).name != "arias_stack"
#
#
# def test_deleting_stack_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting stack."""
#     new_stack = StackRequestModel(
#         name="arias_stack",
#         components={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     new_stack = sql_store["store"].create_stack(
#         stack=new_stack,
#     )
#     sql_store["store"].delete_stack(new_stack.id)
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack(new_stack.id)
#
#
# def test_deleting_nonexistent_stack_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting nonexistent stack fails."""
#     non_existent_stack_id = uuid.uuid4()
#     with pytest.raises(KeyError):
#         sql_store["store"].delete_stack(non_existent_stack_id)
#
#
# def test_deleting_a_stack_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting stack."""
#     # TODO: [server] inject user and project into stack as well
#     new_stack = StackRequestModel(
#         name="arias_stack",
#         components={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     sql_store["store"].create_stack(
#         stack=new_stack,
#     )
#     stacks = sql_store["store"].list_stacks(project_name_or_id=DEFAULT_NAME)
#     assert len(stacks) == 2
#     new_stack = [stack for stack in stacks if stack.name == "arias_stack"][0]
#     sql_store["store"].delete_stack(new_stack.id)
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack(new_stack.id)
#
#
# # ---------
# # Pipelines
# # ---------
#
#
# def test_create_pipeline_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating pipeline."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     pipelines = sql_store["store"].list_pipelines()
#     assert len(pipelines) == 1
#     assert pipelines[0].name == "arias_pipeline"
#
#
# def test_creating_identical_pipeline_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating identical pipeline fails."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     with pytest.raises(EntityExistsError):
#         sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     pipelines = sql_store["store"].list_pipelines()
#     assert len(pipelines) == 1
#
#
# def test_get_pipeline_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting pipeline."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     pipeline_id = sql_store["store"].list_pipelines()[0].id
#     pipeline = sql_store["store"].get_pipeline(pipeline_id=pipeline_id)
#     assert pipeline is not None
#     assert pipeline.name == "arias_pipeline"
#
#
# def test_get_pipeline_fails_for_nonexistent_pipeline(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting pipeline fails for nonexistent pipeline."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_pipeline(uuid.uuid4())
#
#
# def test_list_pipelines_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing pipelines."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     with does_not_raise():
#         pipelines = sql_store["store"].list_pipelines()
#         assert len(pipelines) == 1
#
#
# def test_update_pipeline_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating pipeline."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     new_pipeline = sql_store["store"].create_pipeline(pipeline=new_pipeline)
#
#     pipeline_update = PipelineUpdateModel(
#         name="blupus_ka_pipeline",
#     )
#     with does_not_raise():
#         pipeline_update = sql_store["store"].update_pipeline(
#             pipeline_id=new_pipeline.id, pipeline_update=pipeline_update
#         )
#     assert pipeline_update is not None
#     assert pipeline_update.name == "blupus_ka_pipeline"
#     assert pipeline_update.spec == new_pipeline.spec
#
#
# def test_updating_nonexistent_pipeline_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating nonexistent pipeline fails."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     pipeline_update = PipelineUpdateModel(
#         name="blupus_ka_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     with pytest.raises(KeyError):
#         sql_store["store"].update_pipeline(
#             pipeline_id=uuid.uuid4(), pipeline_update=pipeline_update
#         )
#
#
# def test_deleting_pipeline_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting pipeline."""
#     project_id = sql_store["default_project"].id
#     user_id = sql_store["active_user"].id
#     spec = PipelineSpec(steps=[])
#     new_pipeline = PipelineRequestModel(
#         name="arias_pipeline",
#         project=project_id,
#         user=user_id,
#         spec=spec,
#     )
#     sql_store["store"].create_pipeline(pipeline=new_pipeline)
#     pipeline_id = sql_store["store"].list_pipelines()[0].id
#     sql_store["store"].delete_pipeline(pipeline_id)
#     assert len(sql_store["store"].list_pipelines()) == 0
#     with pytest.raises(KeyError):
#         sql_store["store"].get_pipeline(pipeline_id)
#
#
# def test_deleting_nonexistent_pipeline_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting nonexistent pipeline fails."""
#     with pytest.raises(KeyError):
#         sql_store["store"].delete_pipeline(uuid.uuid4())
#
#
# # --------------
# # Pipeline runs
# # --------------
#
#
# def test_getting_run_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests getting run."""
#     run_id = sql_store_with_run["pipeline_run"].id
#     with does_not_raise():
#         run = sql_store_with_run["store"].get_run(run_id)
#         assert run is not None
#         assert run.name == sql_store_with_run["pipeline_run"].name
#
#
# def test_getting_nonexistent_run_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting nonexistent run fails."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_run(uuid.uuid4())
#
#
# def test_list_runs_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests listing runs."""
#     run = sql_store_with_run["pipeline_run"]
#     with does_not_raise():
#         runs = sql_store_with_run["store"].list_runs()
#         assert len(runs) == 1
#         assert runs[0].name == run.name
#
#
# def test_list_runs_returns_nothing_when_no_runs_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing runs returns nothing when no runs exist."""
#     runs = sql_store["store"].list_runs()
#     assert len(runs) == 0
#
#     with pytest.raises(KeyError):
#         sql_store["store"].list_runs(project_name_or_id=uuid.uuid4())
#
#     false_stack_runs = sql_store["store"].list_runs(stack_id=uuid.uuid4())
#     assert len(false_stack_runs) == 0
#
#     false_run_name_runs = sql_store["store"].list_runs(name="not_arias_run")
#     assert len(false_run_name_runs) == 0
#
#     with pytest.raises(KeyError):
#         sql_store["store"].list_runs(user_name_or_id=uuid.uuid4())
#
#     false_pipeline_runs = sql_store["store"].list_runs(pipeline_id=uuid.uuid4())
#     assert len(false_pipeline_runs) == 0
#
#
# def test_list_runs_is_ordered(sql_store_with_runs):
#     """Tests listing runs returns ordered runs."""
#     runs = sql_store_with_runs["store"].list_runs()
#     assert len(runs) == 10
#     assert all(
#         runs[i].created <= runs[i + 1].created for i in range(len(runs) - 1)
#     )
#
#
# def test_update_run_succeeds(sql_store_with_run):
#     """Tests updating run."""
#     run_id = sql_store_with_run["pipeline_run"].id
#     run = sql_store_with_run["store"].get_run(run_id)
#     assert run.status == ExecutionStatus.COMPLETED
#     run_update = PipelineRunUpdateModel(
#         status=ExecutionStatus.FAILED,
#     )
#     sql_store_with_run["store"].update_run(run_id, run_update)
#     run = sql_store_with_run["store"].get_run(run_id)
#     assert run.status == ExecutionStatus.FAILED
#
#
# def test_update_nonexistent_run_fails(sql_store):
#     """Tests updating nonexistent run fails."""
#     with pytest.raises(KeyError):
#         sql_store["store"].update_run(uuid.uuid4(), PipelineRunUpdateModel())
#
#
# def test_deleting_run_succeeds(sql_store_with_run):
#     """Tests deleting run."""
#     assert len(sql_store_with_run["store"].list_runs()) == 1
#     run_id = sql_store_with_run["pipeline_run"].id
#     sql_store_with_run["store"].delete_run(run_id)
#     assert len(sql_store_with_run["store"].list_runs()) == 0
#     with pytest.raises(KeyError):
#         sql_store_with_run["store"].get_run(run_id)
#
#
# def test_deleting_nonexistent_run_fails(sql_store):
#     """Tests deleting nonexistent run fails."""
#     with pytest.raises(KeyError):
#         sql_store["store"].delete_run(uuid.uuid4())
#
#
# def test_deleting_run_deletes_steps(sql_store_with_run):
#     """Tests deleting run deletes its steps."""
#     assert len(sql_store_with_run["store"].list_run_steps()) == 2
#     run_id = sql_store_with_run["pipeline_run"].id
#     sql_store_with_run["store"].delete_run(run_id)
#     assert len(sql_store_with_run["store"].list_run_steps()) == 0
#
#
# # ------------------
# # Pipeline run steps
# # ------------------
#
#
# def test_get_run_step_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests getting run step."""
#     pipeline_step = sql_store_with_run["step"]
#     run_step = sql_store_with_run["store"].get_run_step(
#         step_run_id=pipeline_step.id
#     )
#     assert run_step is not None
#     assert run_step.id == pipeline_step.id
#     assert run_step == pipeline_step
#
#
# def test_get_run_step_fails_when_step_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting run step fails when step does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_run_step(step_run_id=uuid.uuid4())
#
#
# def test_get_run_step_outputs_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests getting run step outputs."""
#     pipeline_step = sql_store_with_run["step"]
#     store = sql_store_with_run["store"]
#     run_step_outputs = store.get_run_step(pipeline_step.id).output_artifacts
#     assert len(run_step_outputs) == 1
#
#
# def test_get_run_step_inputs_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests getting run step inputs."""
#     pipeline_step = sql_store_with_run["step"]
#     store = sql_store_with_run["store"]
#     run_step_inputs = store.get_run_step(pipeline_step.id).input_artifacts
#     assert len(run_step_inputs) == 1
#
#
# def test_get_run_step_status_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests getting run step status."""
#     pipeline_step = sql_store_with_run["step"]
#     run_step_status = (
#         sql_store_with_run["store"]
#         .get_run_step(step_run_id=pipeline_step.id)
#         .status
#     )
#     assert run_step_status is not None
#     assert isinstance(run_step_status, ExecutionStatus)
#     assert run_step_status == ExecutionStatus.COMPLETED
#
#
# def test_list_run_steps_succeeds(
#     sql_store_with_run: BaseZenStore,
# ):
#     """Tests listing run steps."""
#     run_steps = sql_store_with_run["store"].list_run_steps(
#         run_id=sql_store_with_run["pipeline_run"].id
#     )
#     assert len(run_steps) == 2
#     assert run_steps[1] == sql_store_with_run["step"]
#
#
# def test_update_run_step_succeeds(sql_store_with_run):
#     """Tests updating run step."""
#     step_run = sql_store_with_run["step"]
#     store = sql_store_with_run["store"]
#     step_run = store.get_run_step(step_run_id=step_run.id)
#     assert step_run.status == ExecutionStatus.COMPLETED
#     run_update = StepRunUpdateModel(status=ExecutionStatus.FAILED)
#     updated_run = store.update_run_step(step_run.id, run_update)
#     assert updated_run.status == ExecutionStatus.FAILED
#     step_run = store.get_run_step(step_run_id=step_run.id)
#     assert step_run.status == ExecutionStatus.FAILED
#
#
# def test_update_run_step_fails_when_step_does_not_exist(sql_store):
#     """Tests updating run step fails when step does not exist."""
#     run_update = StepRunUpdateModel(status=ExecutionStatus.FAILED)
#     with pytest.raises(KeyError):
#         sql_store["store"].update_run_step(uuid.uuid4(), run_update)
#
#
# # ---------
# # Artifacts
# # ---------
#
#
# def test_create_artifact_succeeds(sql_store):
#     """Tests creating artifact."""
#     artifact_name = "test_artifact"
#     artifact = ArtifactRequestModel(
#         name=artifact_name,
#         type=ArtifactType.DATA,
#         uri="",
#         materializer="",
#         data_type="",
#         user=sql_store["active_user"].id,
#         project=sql_store["default_project"].id,
#     )
#     with does_not_raise():
#         created_artifact = sql_store["store"].create_artifact(artifact=artifact)
#         assert created_artifact.name == artifact_name
#
#
# def get_artifact_succeeds(sql_store_with_run):
#     """Tests getting artifact."""
#     artifact = sql_store_with_run["store"].get_artifact(
#         artifact_id=sql_store_with_run["artifact"].id
#     )
#     assert artifact is not None
#     assert artifact == sql_store_with_run["artifact"]
#
#
# def test_get_artifact_fails_when_artifact_does_not_exist(sql_store):
#     """Tests getting artifact fails when artifact does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_artifact(artifact_id=uuid.uuid4())
#
#
# def test_list_artifacts_succeeds(sql_store_with_run):
#     """Tests listing artifacts."""
#     artifacts = sql_store_with_run["store"].list_artifacts()
#     assert len(artifacts) == 2
#     assert artifacts[0] == sql_store_with_run["artifact"]
#
#
# def test_list_unused_artifacts(sql_store_with_run):
#     """Tests listing with `unused=True` only returns unused artifacts."""
#     artifacts = sql_store_with_run["store"].list_artifacts()
#     assert len(artifacts) == 2
#     artifacts = sql_store_with_run["store"].list_artifacts(only_unused=True)
#     assert len(artifacts) == 0
#     run_id = sql_store_with_run["pipeline_run"].id
#     sql_store_with_run["store"].delete_run(run_id)
#     artifacts = sql_store_with_run["store"].list_artifacts(only_unused=True)
#     assert len(artifacts) == 2
#
#
# def test_delete_artifact_succeeds(sql_store_with_run):
#     """Tests deleting artifact."""
#     artifact_id = sql_store_with_run["artifact"].id
#     assert len(sql_store_with_run["store"].list_artifacts()) == 2
#     sql_store_with_run["store"].delete_artifact(artifact_id=artifact_id)
#     assert len(sql_store_with_run["store"].list_artifacts()) == 1
#     with pytest.raises(KeyError):
#         sql_store_with_run["store"].get_artifact(artifact_id=artifact_id)
#
#
# def test_delete_artifact_fails_when_artifact_does_not_exist(sql_store):
#     """Tests deleting artifact fails when artifact does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].delete_artifact(artifact_id=uuid.uuid4())
#
#
# # ----------------
# # Stack components
# # ----------------
#
#
# def test_create_stack_component_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating stack component."""
#     stack_component_name = "arias_cat_detection_orchestrator"
#     stack_component = ComponentRequestModel(
#         name=stack_component_name,
#         type=StackComponentType.ORCHESTRATOR,
#         flavor="default",
#         configuration={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         created_component = sql_store["store"].create_stack_component(
#             component=stack_component
#         )
#         assert created_component.name == stack_component_name
#
#
# def test_create_component_fails_when_same_name(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating component fails when same name."""
#     stack_component_name = "nicto"
#     stack_component = ComponentRequestModel(
#         name=stack_component_name,
#         type=StackComponentType.ORCHESTRATOR,
#         flavor="default",
#         configuration={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     sql_store["store"].create_stack_component(component=stack_component)
#     with pytest.raises(StackComponentExistsError):
#         sql_store["store"].create_stack_component(component=stack_component)
#
#
# def test_get_stack_component(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack component."""
#     components = sql_store["default_stack"].components
#     component_id = list(components.values())[0][0].id
#     with does_not_raise():
#         sql_store["store"].get_stack_component(component_id=component_id)
#
#
# def test_get_stack_component_fails_when_component_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack component fails when component does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack_component(component_id=uuid.uuid4())
#
#
# def test_list_stack_components_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack components."""
#     stack_components = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name
#     )
#     assert len(stack_components) == 2
#     component_types = [component.type for component in stack_components]
#     assert StackComponentType.ORCHESTRATOR in component_types
#     assert StackComponentType.ARTIFACT_STORE in component_types
#
#
# def test_list_stack_components_fails_when_project_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack components fails when project does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].list_stack_components(
#             project_name_or_id=uuid.uuid4()
#         )
#
#
# def test_list_stack_components_works_with_filters(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack components works with filters."""
#     artifact_stores = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ARTIFACT_STORE,
#     )
#     assert len(artifact_stores) == 1
#     assert artifact_stores[0].type == StackComponentType.ARTIFACT_STORE
#
#     orchestrators = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ORCHESTRATOR,
#     )
#     assert len(orchestrators) == 1
#     assert orchestrators[0].type == StackComponentType.ORCHESTRATOR
#
#
# def test_list_stack_components_lists_nothing_for_nonexistent_filters(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack components lists nothing for nonexistent filters."""
#     flavor_filtered = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         flavor_name="nonexistent",
#     )
#     assert len(flavor_filtered) == 0
#
#     with pytest.raises(KeyError):
#         sql_store["store"].list_stack_components(
#             project_name_or_id=sql_store["default_project"].name,
#             user_name_or_id=uuid.uuid4(),
#         )
#
#     name_filtered = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         name="nonexistent",
#     )
#     assert len(name_filtered) == 0
#
#
# def test_update_stack_component_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating stack component."""
#     stack_component_name = "aria"
#     stack_component = ComponentRequestModel(
#         name=stack_component_name,
#         type=StackComponentType.ORCHESTRATOR,
#         flavor="default",
#         configuration={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         orchestrator = sql_store["store"].create_stack_component(
#             component=stack_component
#         )
#
#     updated_orchestrator_name = "axl"
#     component_update = ComponentUpdateModel(name=updated_orchestrator_name)
#     with does_not_raise():
#         updated_component = sql_store["store"].update_stack_component(
#             component_id=orchestrator.id, component_update=component_update
#         )
#         assert updated_component.name == updated_orchestrator_name
#
#
# def test_update_default_stack_component_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
# ):
#     """Tests that updating default stack components fails."""
#     default_artifact_store = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ARTIFACT_STORE,
#         name="default",
#     )[0]
#
#     default_orchestrator = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ORCHESTRATOR,
#         name="default",
#     )[0]
#
#     component_update = ComponentUpdateModel(name="aria")
#     with pytest.raises(IllegalOperationError):
#         sql_store["store"].update_stack_component(
#             component_id=default_orchestrator.id,
#             component_update=component_update,
#         )
#
#     default_orchestrator.name = "axl"
#     with pytest.raises(IllegalOperationError):
#         sql_store["store"].update_stack_component(
#             component_id=default_artifact_store.id,
#             component_update=component_update,
#         )
#
#
# def test_update_stack_component_fails_when_component_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests updating stack component fails when component does not exist."""
#     stack_component = ComponentUpdateModel(
#         name="nonexistent",
#         type=StackComponentType.ORCHESTRATOR,
#         flavor="default",
#         configuration={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with pytest.raises(KeyError):
#         sql_store["store"].update_stack_component(
#             component_id=uuid.uuid4(), component_update=stack_component
#         )
#
#
# def test_delete_stack_component_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting stack component."""
#     stack_component_name = "arias_cat_detection_orchestrator"
#     stack_component = ComponentRequestModel(
#         name=stack_component_name,
#         type=StackComponentType.ORCHESTRATOR,
#         flavor="default",
#         configuration={},
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     created_component = sql_store["store"].create_stack_component(
#         component=stack_component
#     )
#     orchestrators = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ORCHESTRATOR,
#     )
#     assert len(orchestrators) == 2
#     with does_not_raise():
#         sql_store["store"].delete_stack_component(
#             component_id=created_component.id
#         )
#         orchestrators = sql_store["store"].list_stack_components(
#             project_name_or_id=sql_store["default_project"].name,
#             type=StackComponentType.ORCHESTRATOR,
#         )
#     assert len(orchestrators) == 1
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack_component(
#             component_id=created_component.id
#         )
#
#
# def test_delete_default_stack_component_fails(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests that deleting default stack components is prohibited."""
#     default_artifact_store = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ARTIFACT_STORE,
#         name="default",
#     )[0]
#
#     default_orchestrator = sql_store["store"].list_stack_components(
#         project_name_or_id=sql_store["default_project"].name,
#         type=StackComponentType.ORCHESTRATOR,
#         name="default",
#     )[0]
#
#     with pytest.raises(IllegalOperationError):
#         sql_store["store"].delete_stack_component(default_artifact_store.id)
#
#     with pytest.raises(IllegalOperationError):
#         sql_store["store"].delete_stack_component(default_orchestrator.id)
#
#
# def test_delete_stack_component_fails_when_component_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests deleting stack component fails when component does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].delete_stack_component(component_id=uuid.uuid4())
#
#
# # -----------------------
# # Stack component flavors
# # -----------------------
#
#
# def test_create_stack_component_flavor_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating stack component flavor."""
#     flavor_name = "blupus"
#     blupus_flavor = FlavorRequestModel(
#         name=flavor_name,
#         type=StackComponentType.ORCHESTRATOR,
#         config_schema="default",
#         source=".",
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         sql_store["store"].create_flavor(flavor=blupus_flavor)
#         blupus_flavor_id = (
#             sql_store["store"]
#             .list_flavors(
#                 project_name_or_id=sql_store["default_project"].name,
#                 component_type=StackComponentType.ORCHESTRATOR,
#                 name=flavor_name,
#             )[0]
#             .id
#         )
#         created_flavor = sql_store["store"].get_flavor(
#             flavor_id=blupus_flavor_id
#         )
#         assert created_flavor.name == flavor_name
#
#
# def test_create_stack_component_fails_when_flavor_already_exists(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests creating stack component flavor fails when flavor already exists."""
#     flavor_name = "scinda"
#     scinda_flavor = FlavorRequestModel(
#         name=flavor_name,
#         type=StackComponentType.ORCHESTRATOR,
#         config_schema="default",
#         source=".",
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         sql_store["store"].create_flavor(flavor=scinda_flavor)
#     scinda_copy_flavor = FlavorRequestModel(
#         name=flavor_name,
#         type=StackComponentType.ORCHESTRATOR,
#         config_schema="default",
#         source=".",
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with pytest.raises(EntityExistsError):
#         sql_store["store"].create_flavor(flavor=scinda_copy_flavor)
#
#
# def test_get_flavor_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack component flavor."""
#     flavor_name = "verata"
#     verata_flavor = FlavorRequestModel(
#         name=flavor_name,
#         type=StackComponentType.ARTIFACT_STORE,
#         config_schema="default",
#         source=".",
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         new_flavor = sql_store["store"].create_flavor(flavor=verata_flavor)
#
#         assert (
#             sql_store["store"].get_flavor(flavor_id=new_flavor.id).name
#             == flavor_name
#         )
#
#
# def test_get_flavor_fails_when_flavor_does_not_exist(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests getting stack component flavor fails when flavor does not exist."""
#     with pytest.raises(KeyError):
#         sql_store["store"].get_flavor(flavor_id=uuid.uuid4())
#
#
# def test_list_flavors_succeeds(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack component flavors."""
#     flavor_name = "verata"
#     verata_flavor = FlavorRequestModel(
#         name=flavor_name,
#         type=StackComponentType.ARTIFACT_STORE,
#         config_schema="default",
#         source=".",
#         project=sql_store["default_project"].id,
#         user=sql_store["active_user"].id,
#     )
#     with does_not_raise():
#         sql_store["store"].create_flavor(flavor=verata_flavor)
#         assert len(sql_store["store"].list_flavors()) == 1
#         assert sql_store["store"].list_flavors()[0].name == flavor_name
#
#
# def test_list_flavors_fails_with_nonexistent_project(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stack component flavors fails with nonexistent project."""
#     with pytest.raises(KeyError):
#         sql_store["store"].list_flavors(
#             project_name_or_id="nonexistent",
#             component_type=StackComponentType.ORCHESTRATOR,
#         )
