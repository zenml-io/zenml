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

import pytest

from tests.integration.functional.zen_stores.utils import (
    CrudTestConfig,
    PipelineRunContext,
    RoleContext,
    TeamContext,
    UserContext,
    list_of_entities,
    sample_name,
)
from zenml.client import Client
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import (
    ArtifactFilterModel,
    ComponentFilterModel,
    ComponentUpdateModel,
    PipelineRunFilterModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleUpdateModel,
    StackUpdateModel,
    StepRunFilterModel,
    TeamRequestModel,
    TeamRoleAssignmentRequestModel,
    TeamUpdateModel,
    UserRequestModel,
    UserRoleAssignmentRequestModel,
    UserUpdateModel,
    WorkspaceFilterModel,
    WorkspaceUpdateModel,
)
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
)
from zenml.zen_stores.base_zen_store import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_GUEST_ROLE,
    DEFAULT_STACK_NAME,
    DEFAULT_USERNAME,
    DEFAULT_WORKSPACE_NAME,
)

DEFAULT_NAME = "default"

# .--------------.
# | GENERIC CRUD |
# '--------------'


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
    if isinstance(create_model, WorkspaceScopedRequestModel):
        create_model.user = client.active_user.id
        create_model.workspace = client.active_workspace.id
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
    if crud_test_config.update_model:
        # Update the created entity
        update_model = crud_test_config.update_model
        with does_not_raise():
            updated_entity = crud_test_config.update_method(
                created_entity.id, update_model
            )
        # Ids should remain the same
        assert updated_entity.id == created_entity.id
        # Something in the Model should have changed
        assert updated_entity.json() != created_entity.json()

    # Cleanup
    with does_not_raise():
        crud_test_config.delete_method(created_entity.id)
    # Filter by name to verify the entity was actually deleted
    with pytest.raises(KeyError):
        crud_test_config.get_method(created_entity.id)
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
    if crud_test_config.entity_name == "artifact":
        # Artifacts do not check for duplicates
        pytest.skip()

    client = Client()
    # Create the entity
    create_model = crud_test_config.create_model
    if isinstance(create_model, WorkspaceScopedRequestModel):
        create_model.user = client.active_user.id
        create_model.workspace = client.active_workspace.id
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
    if crud_test_config.update_model:
        # Update the created entity
        update_model = crud_test_config.update_model
        with pytest.raises(KeyError):
            crud_test_config.update_method(uuid.uuid4(), update_model)
    else:
        pytest.skip()


@pytest.mark.parametrize(
    "crud_test_config",
    list_of_entities,
    ids=[e.entity_name for e in list_of_entities],
)
def test_deleting_nonexistent_workspace_raises_error(
    crud_test_config: CrudTestConfig,
):
    """Tests deleting a nonexistent workspace raises an error."""
    with pytest.raises(KeyError):
        crud_test_config.delete_method(uuid.uuid4())


# .----------.
# | WORKSPACES |
# '----------'


def test_only_one_default_workspace_present():
    """Tests that one and only one default workspace is present."""
    client = Client()
    assert (
        len(
            client.zen_store.list_workspaces(
                WorkspaceFilterModel(name="default")
            )
        )
        == 1
    )


def test_updating_default_workspace_fails():
    """Tests updating the default workspace."""
    client = Client()

    default_workspace = client.zen_store.get_workspace(DEFAULT_WORKSPACE_NAME)
    assert default_workspace.name == DEFAULT_WORKSPACE_NAME
    workspace_update = WorkspaceUpdateModel(
        name="aria_workspace",
        description="Aria has taken possession of this workspace.",
    )
    with pytest.raises(IllegalOperationError):
        client.zen_store.update_workspace(
            workspace_id=default_workspace.id,
            workspace_update=workspace_update,
        )


def test_deleting_default_workspace_fails():
    """Tests deleting the default workspace."""
    client = Client()
    with pytest.raises(IllegalOperationError):
        client.zen_store.delete_workspace(DEFAULT_NAME)


# .-------.-.
# | TEAMS | |
# '-------'-'


def test_adding_user_to_team():
    """Tests adding a user to a team."""
    zen_store = Client().zen_store
    team_name = "arias_team"
    with UserContext() as created_user:
        try:
            new_team = TeamRequestModel(name=team_name)
            new_team = zen_store.create_team(new_team)

            team_update = TeamUpdateModel(users=[created_user.id])
            team_update = zen_store.update_team(
                team_id=new_team.id, team_update=team_update
            )

            assert created_user.id in team_update.user_ids
            assert len(team_update.users) == 1

            # Make sure the team name has not been inadvertently changed
            assert zen_store.get_team(new_team.id).name == team_name
        # Cleanup no matter what
        finally:
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
    team_name = sample_name("arias_team")

    with UserContext() as created_user:
        try:
            new_team = TeamRequestModel(
                name=team_name, users=[created_user.id]
            )
            new_team = zen_store.create_team(new_team)
            assert created_user.id in new_team.user_ids

            team_update = TeamUpdateModel(users=[])
            team_update = zen_store.update_team(
                team_id=new_team.id, team_update=team_update
            )

            assert created_user.id not in team_update.user_ids
        # Cleanup no matter what
        finally:
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


# .-------.
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
        workspace=None,
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


# .------------------.
# | ROLE ASSIGNMENTS |
# '------------------'


def test_assigning_role_to_user_succeeds():
    """Tests assigning a role to a user."""
    zen_store = Client().zen_store

    with RoleContext() as created_role:
        with UserContext() as created_user:
            role_assignment = UserRoleAssignmentRequestModel(
                role=created_role.id,
                user=created_user.id,
                workspace=None,
            )
            with does_not_raise():
                assignment = zen_store.create_user_role_assignment(
                    role_assignment
                )

    # With user and role deleted the assignment should be deleted as well
    with pytest.raises(KeyError):
        zen_store.delete_user_role_assignment(assignment.id)


def test_assigning_role_to_team_succeeds():
    """Tests assigning a role to a user."""
    zen_store = Client().zen_store

    with RoleContext() as created_role:
        with TeamContext() as created_team:
            role_assignment = TeamRoleAssignmentRequestModel(
                role=created_role.id,
                team=created_team.id,
                workspace=None,
            )
            with does_not_raise():
                assignment = zen_store.create_team_role_assignment(
                    role_assignment
                )
    # With user and role deleted the assignment should be deleted as well
    with pytest.raises(KeyError):
        zen_store.delete_team_role_assignment(assignment.id)


def test_assigning_role_if_assignment_already_exists_fails():
    """Tests assigning a role to a user if the assignment already exists."""
    zen_store = Client().zen_store

    with RoleContext() as created_role:
        with UserContext() as created_user:

            role_assignment = UserRoleAssignmentRequestModel(
                role=created_role.id,
                user=created_user.id,
                workspace=None,
            )
            with does_not_raise():
                (zen_store.create_user_role_assignment(role_assignment))
            with pytest.raises(EntityExistsError):
                (zen_store.create_user_role_assignment(role_assignment))


def test_revoking_role_for_user_succeeds():
    """Tests revoking a role for a user."""
    zen_store = Client().zen_store

    with RoleContext() as created_role:
        with UserContext() as created_user:
            role_assignment = UserRoleAssignmentRequestModel(
                role=created_role.id,
                user=created_user.id,
                workspace=None,
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


def test_revoking_role_for_team_succeeds():
    """Tests revoking a role for a team."""
    zen_store = Client().zen_store

    with RoleContext() as created_role:
        with TeamContext() as created_team:
            role_assignment = TeamRoleAssignmentRequestModel(
                role=created_role.id,
                team=created_team.id,
                workspace=None,
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


# .------------------.
# | Stack components |
# '------------------'

# TODO: tests regarding sharing of components missing


def test_update_default_stack_component_fails():
    """Tests that updating default stack components fails."""
    client = Client()
    store = client.zen_store
    default_artifact_store = store.list_stack_components(
        ComponentFilterModel(
            workspace_id=client.active_workspace.id,
            type=StackComponentType.ARTIFACT_STORE,
            name="default",
        )
    )[0]

    default_orchestrator = store.list_stack_components(
        ComponentFilterModel(
            workspace_id=client.active_workspace.id,
            type=StackComponentType.ORCHESTRATOR,
            name="default",
        )
    )[0]

    component_update = ComponentUpdateModel(name="aria")
    with pytest.raises(IllegalOperationError):
        store.update_stack_component(
            component_id=default_orchestrator.id,
            component_update=component_update,
        )

    default_orchestrator.name = "axl"
    with pytest.raises(IllegalOperationError):
        store.update_stack_component(
            component_id=default_artifact_store.id,
            component_update=component_update,
        )


def test_delete_default_stack_component_fails():
    """Tests that deleting default stack components is prohibited."""
    client = Client()
    store = client.zen_store
    default_artifact_store = store.list_stack_components(
        ComponentFilterModel(
            workspace_id=client.active_workspace.id,
            type=StackComponentType.ARTIFACT_STORE,
            name="default",
        )
    )[0]

    default_orchestrator = store.list_stack_components(
        ComponentFilterModel(
            workspace_id=client.active_workspace.id,
            type=StackComponentType.ORCHESTRATOR,
            name="default",
        )
    )[0]

    with pytest.raises(IllegalOperationError):
        store.delete_stack_component(default_artifact_store.id)

    with pytest.raises(IllegalOperationError):
        store.delete_stack_component(default_orchestrator.id)


# .-------------------------.
# | Stack component flavors |
# '-------------------------'

# .--------.
# | STACKS |
# '--------'


def test_updating_default_stack_fails():
    """Tests that updating the default stack is prohibited."""
    client = Client()

    default_stack = client.get_stack(DEFAULT_STACK_NAME)
    assert default_stack.name == DEFAULT_WORKSPACE_NAME
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
# def test_list_stacks_fails_with_nonexistent_workspace(
#     sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
# ):
#     """Tests listing stacks fails with nonexistent workspace."""
#     with pytest.raises(KeyError):
#         sql_store["store"].list_stacks(workspace_name_or_id=uuid.uuid4())
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
#         workspace=sql_store["default_workspace"].id,
#         user=sql_store["active_user"].id,
#     )
#     # TODO: [server] inject user and workspace into stack as well
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
#         workspace=sql_store["default_workspace"].id,
#         user=sql_store["active_user"].id,
#     )
#     with pytest.raises(StackExistsError):
#         # TODO: [server] inject user and workspace into stack as well
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
#         workspace=sql_store["default_workspace"].id,
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
#         workspace=sql_store["default_workspace"].id,
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
#     # TODO: [server] inject user and workspace into stack as well
#     new_stack = StackRequestModel(
#         name="arias_stack",
#         components={},
#         workspace=sql_store["default_workspace"].id,
#         user=sql_store["active_user"].id,
#     )
#     sql_store["store"].create_stack(
#         stack=new_stack,
#     )
#     stacks = sql_store["store"].list_stacks(workspace_name_or_id=DEFAULT_NAME)
#     assert len(stacks) == 2
#     new_stack = [stack for stack in stacks if stack.name == "arias_stack"][0]
#     sql_store["store"].delete_stack(new_stack.id)
#     with pytest.raises(KeyError):
#         sql_store["store"].get_stack(new_stack.id)


# .-----------.
# | Pipelines |
# '-----------'

# .----------------.
# | Pipeline runs  |
# '----------------'


def test_list_runs_is_ordered():
    """Tests listing runs returns ordered runs."""
    client = Client()
    store = client.zen_store

    num_pipelines_before = store.list_runs(PipelineRunFilterModel()).total

    num_runs = 5
    with PipelineRunContext(num_runs):

        pipelines = store.list_runs(PipelineRunFilterModel()).items
        assert len(pipelines) == num_pipelines_before + num_runs
        assert all(
            pipelines[i].created <= pipelines[i + 1].created
            for i in range(len(pipelines) - 1)
        )


def test_deleting_run_deletes_steps():
    """Tests deleting run deletes its steps."""
    client = Client()
    store = client.zen_store

    # Just in case the test db is not in a clean state we compare relative
    num_steps_before = store.list_run_steps(StepRunFilterModel()).total
    num_pipelines_before = store.list_runs(PipelineRunFilterModel()).total

    num_runs = 1

    with PipelineRunContext(num_runs) as runs:
        steps = store.list_run_steps(StepRunFilterModel())

        assert steps.total == num_steps_before + num_runs * 2
        pipelines = store.list_runs(PipelineRunFilterModel())
        assert pipelines.total == num_pipelines_before + num_runs
        run_id = runs[0].id
        store.delete_run(run_id)
        assert (
            len(store.list_run_steps(StepRunFilterModel())) == num_steps_before
        )


# .--------------------.
# | Pipeline run steps |
# '--------------------'


def test_get_run_step_outputs_succeeds():
    """Tests getting run step outputs."""
    client = Client()
    store = client.zen_store

    with PipelineRunContext(1):
        steps = store.list_run_steps(StepRunFilterModel(name="step_2"))

        for step in steps.items:
            run_step_outputs = store.get_run_step(step.id).output_artifacts
            assert len(run_step_outputs) == 1


def test_get_run_step_inputs_succeeds():
    """Tests getting run step inputs."""
    client = Client()
    store = client.zen_store

    with PipelineRunContext(1):

        steps = store.list_run_steps(StepRunFilterModel(name="step_2"))
        for step in steps.items:
            run_step_inputs = store.get_run_step(step.id).input_artifacts
            assert len(run_step_inputs) == 1


# .-----------.
# | Artifacts |
# '-----------'


def test_list_unused_artifacts():
    """Tests listing with `unused=True` only returns unused artifacts."""
    client = Client()
    store = client.zen_store

    num_artifacts_before = store.list_artifacts(ArtifactFilterModel()).total
    num_unused_artifacts_before = store.list_artifacts(
        ArtifactFilterModel(only_unused=True)
    ).total
    num_runs = 1
    with PipelineRunContext(num_runs):

        artifacts = store.list_artifacts(ArtifactFilterModel())
        assert artifacts.total == num_artifacts_before + num_runs * 2

        artifacts = store.list_artifacts(ArtifactFilterModel(only_unused=True))
        assert artifacts.total == num_unused_artifacts_before


def test_artifacts_are_not_deleted_with_run():
    """Tests listing with `unused=True` only returns unused artifacts."""
    client = Client()
    store = client.zen_store

    num_artifacts_before = store.list_artifacts(ArtifactFilterModel()).total
    num_runs = 1
    with PipelineRunContext(num_runs):

        artifacts = store.list_artifacts(ArtifactFilterModel())
        assert artifacts.total == num_artifacts_before + num_runs * 2

        # Cleanup
        pipelines = store.list_runs(PipelineRunFilterModel()).items
        for p in pipelines:
            store.delete_run(p.id)

        artifacts = store.list_artifacts(ArtifactFilterModel())
        assert artifacts.total == num_artifacts_before + num_runs * 2
