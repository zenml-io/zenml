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
from ml_metadata.proto.metadata_store_pb2 import ConnectionConfig

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus, PermissionType, StackComponentType
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.models.pipeline_models import PipelineModel
from zenml.new_models import (
    ComponentRequestModel,
    FlavorRequestModel,
    ProjectRequestModel,
    ProjectUpdateModel,
    RoleRequestModel,
    StackRequestModel,
    TeamRequestModel,
    UserRequestModel, StackUpdateModel,
)
from zenml.zen_stores.base_zen_store import BaseZenStore

DEFAULT_NAME = "default"

#  .--------
# | PROJECTS
# '---------


def test_only_one_default_project(sql_store: BaseZenStore):
    """Tests that only one default project can be created."""
    assert len(sql_store["store"].list_projects()) == 1


def test_project_creation(sql_store: BaseZenStore):
    """Tests project creation."""
    new_project = ProjectRequestModel(name="arias_project")
    sql_store["store"].create_project(new_project)
    projects_list = sql_store["store"].list_projects()
    assert len(projects_list) == 2
    assert projects_list[1].name == "arias_project"


def test_getting_project(sql_store: BaseZenStore):
    """Tests getting a project."""
    assert sql_store["default_project"].name == DEFAULT_NAME
    assert type(sql_store["default_project"].id) == uuid.UUID


def test_getting_nonexistent_project_raises_error(
    sql_store: BaseZenStore,
):
    """Tests getting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_project("blupus_project")


def test_updating_default_project_fails(sql_store: BaseZenStore):
    """Tests updating the default project."""
    default_project = sql_store["default_project"]
    assert default_project.name == DEFAULT_NAME
    default_project.name = "aria"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_project(default_project)


def test_updating_project(sql_store: BaseZenStore):
    """Tests updating a project."""
    new_project = ProjectRequestModel(name="arias_project")
    new_project = sql_store["store"].create_project(new_project)
    new_name = "axls_project"
    with does_not_raise():
        updated_project = sql_store["store"].get_project(
            project_name_or_id="arias_project"
        )
    project_update = ProjectUpdateModel(name=new_name)
    with does_not_raise():
        sql_store["store"].update_project(
            project_id=new_project.id, project_update=project_update
        )
    with does_not_raise():
        updated_project = sql_store["store"].get_project(
            project_name_or_id=new_name
        )


def test_updating_nonexisting_project_raises_error(
    sql_store: BaseZenStore,
):
    """Tests updating a nonexistent project raises an error."""
    new_project = ProjectRequestModel(name="arias_project")
    with pytest.raises(KeyError):
        sql_store["store"].update_project(new_project)


def test_deleting_project_succeeds(sql_store: BaseZenStore):
    """Tests deleting a project."""
    new_project = ProjectRequestModel(name="axls_project")
    new_project = sql_store["store"].create_project(new_project)
    with does_not_raise():
        sql_store["store"].delete_project("axls_project")
    assert len(sql_store["store"].list_projects()) == 1


def test_deleting_default_project_fails(sql_store: BaseZenStore):
    """Tests deleting the default project."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_project(DEFAULT_NAME)


def test_deleting_nonexistent_project_raises_error(
    sql_store: BaseZenStore,
):
    """Tests deleting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_project("blupus_project")


#  .-----
# | TEAMS
# '------


def test_list_teams(sql_store: BaseZenStore):
    """Tests listing teams."""
    assert len(sql_store["store"].teams) == 0


def test_create_team(sql_store: BaseZenStore):
    """Tests creating a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert len(sql_store["store"].teams) == 1
    assert sql_store["store"].teams[0].name == "arias_team"


def test_get_team(sql_store: BaseZenStore):
    """Tests getting a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert sql_store["store"].get_team("arias_team").name == "arias_team"


def test_get_nonexistent_team_raises_error(sql_store: BaseZenStore):
    """Tests getting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_team("blupus_team")


def test_delete_team_works(sql_store: BaseZenStore):
    """Tests deleting a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert len(sql_store["store"].teams) == 1
    new_team_id = sql_store["store"].get_team("arias_team").id
    sql_store["store"].delete_team(new_team_id)
    assert len(sql_store["store"].teams) == 0


def test_nonexistent_team_raises_error(sql_store: BaseZenStore):
    """Tests deleting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_team(uuid.uuid4())


def test_adding_user_to_team(sql_store: BaseZenStore):
    """Tests adding a user to a team."""
    assert len(sql_store["store"].teams) == 0
    team_name = "arias_team"
    new_team = TeamRequestModel(name=team_name)
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    sql_store["store"].add_user_to_team(
        user_name_or_id=DEFAULT_NAME, team_name_or_id=team_name
    )
    assert (
        sql_store["store"].get_users_for_team(team_name)[0].id
        == current_user_id
    )


def test_adding_nonexistent_user_to_nonexistent_team_raises_error(
    sql_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].add_user_to_team(uuid.uuid4(), uuid.uuid4())


def test_adding_nonexistent_user_to_real_team_raises_error(
    sql_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    new_team_id = sql_store["store"].get_team("arias_team").id
    with pytest.raises(KeyError):
        sql_store["store"].add_user_to_team(uuid.uuid4(), new_team_id)


def test_adding_real_user_to_nonexistent_team_raises_error(
    sql_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    current_user_id = sql_store["active_user"].id
    with pytest.raises(KeyError):
        sql_store["store"].add_user_to_team(current_user_id, uuid.uuid4())


def test_removing_user_from_team_succeeds(sql_store: BaseZenStore):
    """Tests removing a user from a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    new_team_id = sql_store["store"].get_team("arias_team").id
    sql_store["store"].add_user_to_team(current_user_id, new_team_id)
    assert len(sql_store["store"].get_users_for_team(new_team_id)) == 1
    sql_store["store"].remove_user_from_team(current_user_id, new_team_id)
    assert len(sql_store["store"].get_users_for_team(new_team_id)) == 0


def test_removing_nonexistent_user_from_team_fails(
    sql_store: BaseZenStore,
):
    """Tests removing a nonexistent user from a team raises an error."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    new_team_id = sql_store["store"].get_team("arias_team").id
    with pytest.raises(KeyError):
        sql_store["store"].remove_user_from_team(uuid.uuid4(), new_team_id)


def test_getting_user_from_nonexistent_team_fails(
    sql_store: BaseZenStore,
):
    """Tests getting a user from a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_users_for_team(uuid.uuid4())


def test_getting_user_for_team(sql_store: BaseZenStore):
    """Tests getting a user from a team."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    new_team_id = sql_store["store"].get_team("arias_team").id
    sql_store["store"].add_user_to_team(current_user_id, new_team_id)
    users_for_team = sql_store["store"].get_users_for_team(new_team_id)
    assert len(users_for_team) == 1
    assert users_for_team[0].id == current_user_id


def test_getting_team_for_user(sql_store: BaseZenStore):
    """Tests getting a team for a user."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    new_team_id = sql_store["store"].get_team("arias_team").id
    sql_store["store"].add_user_to_team(current_user_id, new_team_id)
    teams_for_user = sql_store["store"].get_teams_for_user(current_user_id)
    assert len(teams_for_user) == 1
    assert teams_for_user[0].id == new_team_id


#  .------.
# | USERS |
# '-------'


def test_active_user_property(sql_store: BaseZenStore):
    """Tests the active user property."""
    active_user = sql_store["store"].active_user
    assert active_user is not None
    assert active_user == sql_store["active_user"]


def test_active_user_name_property(sql_store: BaseZenStore):
    """Tests the active user name property."""
    active_user_name = sql_store["store"].active_user_name
    assert active_user_name is not None
    assert active_user_name == sql_store["active_user"].name
    assert active_user_name == DEFAULT_NAME


def test_users_property(sql_store: BaseZenStore):
    """Tests the users property."""
    assert len(sql_store["store"].users) == 1
    assert sql_store["store"].users[0].name == DEFAULT_NAME
    assert sql_store["active_user"].name == DEFAULT_NAME
    assert sql_store["store"].users[0] == sql_store["store"].active_user
    assert sql_store["store"].users[0] == sql_store["active_user"]


def test_creating_user_succeeds(sql_store: BaseZenStore):
    """Tests creating a user."""
    assert len(sql_store["store"].users) == 1
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    assert len(sql_store["store"].users) == 2
    assert sql_store["store"].get_user("aria") is not None


def test_creating_user_with_existing_name_fails(
    sql_store: BaseZenStore,
):
    """Tests creating a user with an existing name fails."""
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_user(new_user)


def test_getting_nonexistent_user_fails(sql_store: BaseZenStore):
    """Tests getting a nonexistent user fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_user("aria")


def test_getting_user_by_name_and_id_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting a user by name and id."""
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    users = sql_store["store"].users
    new_user_id = str(users[1].id)
    user_by_name = sql_store["store"].get_user("aria")
    user_by_id = sql_store["store"].get_user(new_user_id)
    assert user_by_id == user_by_name
    assert len(users) == 2


def test_updating_user_succeeds(sql_store: BaseZenStore):
    """Tests updating a user."""
    new_user_model = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user_model)
    new_user = sql_store["store"].get_user("aria")
    new_user.name = "blupus"
    sql_store["store"].update_user(new_user)
    assert sql_store["store"].get_user("blupus") is not None
    with pytest.raises(KeyError):
        sql_store["store"].get_user("aria")


def test_updating_default_user_fails(sql_store: BaseZenStore):
    """Tests that updating the default user is prohibited."""
    default_user = sql_store["store"].get_user("default")
    default_user.name = "axl"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_user(default_user)


def test_updating_nonexistent_user_fails(sql_store: BaseZenStore):
    """Tests updating a nonexistent user fails."""
    new_user = UserRequestModel(name="demonic_aria")
    with pytest.raises(KeyError):
        sql_store["store"].update_user(new_user)


def test_deleting_user_succeeds(sql_store: BaseZenStore):
    """Tests deleting a user."""
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    new_user_id = sql_store["store"].get_user("aria").id
    assert len(sql_store["store"].users) == 2
    sql_store["store"].delete_user(new_user_id)
    assert len(sql_store["store"].users) == 1


def test_deleting_default_user_fails(sql_store: BaseZenStore):
    """Tests that deleting the default user is prohibited."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_user("default")


#  .------.
# | ROLES |
# '-------'


def test_roles_property_with_fresh_store(sql_store: BaseZenStore):
    """Tests the roles property with a fresh ZenStore."""
    assert len(sql_store["store"].roles) == 2


def test_creating_role(sql_store: BaseZenStore):
    """Tests creating a role."""
    assert len(sql_store["store"].roles) == 2
    roles_before = len(sql_store["store"].roles)

    new_role = RoleRequestModel(
        name="admin",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_role(new_role)

    new_role = RoleRequestModel(
        name="cat",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == roles_before + 1
    assert sql_store["store"].get_role("admin") is not None


def test_creating_role_with_empty_permissions_succeeds(sql_store: BaseZenStore):
    """Tests creating a role."""
    assert len(sql_store["store"].roles) == 2
    roles_before = len(sql_store["store"].roles)

    new_role = RoleRequestModel(name="cat", permissions=set())
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == roles_before + 1
    assert sql_store["store"].get_role("admin") is not None


def test_creating_role_with_existing_name_fails(sql_store: BaseZenStore):
    """Tests creating a role that already exists."""
    new_role = RoleRequestModel(
        name="admin",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_role(new_role)


def test_creating_existing_role_fails(sql_store: BaseZenStore):
    """Tests creating an existing role fails."""
    roles_before = len(sql_store["store"].roles)
    new_role = RoleRequestModel(
        name="admin",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == roles_before


def test_getting_role_succeeds(sql_store: BaseZenStore):
    """Tests getting a role."""
    new_role = RoleRequestModel(
        name="cat_feeder",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )

    sql_store["store"].create_role(new_role)
    assert sql_store["store"].get_role("cat_feeder") is not None


def test_getting_nonexistent_role_fails(sql_store: BaseZenStore):
    """Tests getting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_role("random_role_that_does_not_exist")


def test_deleting_role_succeeds(sql_store: BaseZenStore):
    """Tests deleting a role."""
    roles_before = len(sql_store["store"].roles)

    new_role = RoleRequestModel(
        name="cat_feeder", permissions={PermissionType.ME}
    )
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == roles_before + 1
    new_role_id = str(sql_store["store"].get_role("cat_feeder").id)
    sql_store["store"].delete_role(new_role_id)
    assert len(sql_store["store"].roles) == roles_before
    with pytest.raises(KeyError):
        sql_store["store"].get_role(new_role_id)


def test_deleting_nonexistent_role_fails(sql_store: BaseZenStore):
    """Tests deleting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_role(uuid.uuid4())


def test_deleting_builtin_role_fails(sql_store: BaseZenStore):
    """Tests deleting a built-in role fails."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_role("admin")

    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_role("guest")


def test_updating_builtin_role_fails(sql_store: BaseZenStore):
    """Tests updating a built-in role fails."""
    role = sql_store["store"].get_role("admin")
    role.name = "new_name"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_role(role)

    role = sql_store["store"].get_role("guest")
    role.name = "new_name"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_role(role)


#  .----------------
# | ROLE ASSIGNMENTS
# '-----------------


def test_assigning_role_to_user_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user."""
    roles_before = len(sql_store_with_team["store"].roles)
    role_assignments_before = len(sql_store_with_team["store"].role_assignments)

    new_role = RoleRequestModel(
        name="aria_feeder", permissions={PermissionType.ME}
    )
    current_user_id = sql_store_with_team["active_user"].id

    sql_store["store"].create_role(new_role)
    new_role_id = sql_store_with_team["store"].get_role("aria_feeder").id
    sql_store["store"].assign_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == roles_before + 1
    assert (
        len(sql_store_with_team["store"].role_assignments)
        == role_assignments_before + 1
    )


def test_assigning_role_to_team_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a team."""
    roles_before = len(sql_store_with_team["store"].roles)
    role_assignments_before = len(sql_store_with_team["store"].role_assignments)

    team_id = sql_store_with_team["default_team"].id
    new_role = RoleRequestModel(
        name="blupus_friend", permissions={PermissionType.ME}
    )
    sql_store["store"].create_role(new_role)
    new_role_id = sql_store_with_team["store"].get_role("blupus_friend").id
    sql_store["store"].assign_role(new_role_id, team_id, is_user=False)

    assert len(sql_store_with_team["store"].roles) == roles_before + 1
    assert (
        len(sql_store_with_team["store"].role_assignments)
        == role_assignments_before + 1
    )
    assert (
        len(
            sql_store["store"].list_role_assignments(
                user_name_or_id=sql_store_with_team["active_user"].id
            )
        )
        == 2
    )


def test_assigning_role_if_assignment_already_exists(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user if the assignment already exists."""
    roles_before = len(sql_store_with_team["store"].roles)
    role_assignments_before = len(sql_store_with_team["store"].role_assignments)

    new_role = RoleRequestModel(
        name="aria_feeder",
        permissions={
            PermissionType.ME,
            PermissionType.READ,
            PermissionType.WRITE,
        },
    )
    current_user_id = sql_store_with_team["active_user"].id
    sql_store["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    sql_store["store"].assign_role(new_role_id, current_user_id)
    with pytest.raises(EntityExistsError):
        sql_store["store"].assign_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == roles_before + 1
    assert (
        len(sql_store_with_team["store"].role_assignments)
        == role_assignments_before + 1
    )


def test_revoking_role_for_user_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a user."""
    roles_before = len(sql_store_with_team["store"].roles)
    role_assignments_before = len(sql_store_with_team["store"].role_assignments)

    new_role = RoleRequestModel(
        name="aria_feeder", permissions={PermissionType.ME}
    )
    current_user_id = sql_store_with_team["active_user"].id
    sql_store["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    sql_store["store"].assign_role(new_role_id, current_user_id)
    sql_store["store"].revoke_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == roles_before + 1
    assert (
        len(sql_store_with_team["store"].role_assignments)
        == role_assignments_before
    )


def test_revoking_role_for_team_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a team."""
    roles_before = len(sql_store_with_team["store"].roles)
    role_assignments_before = len(sql_store_with_team["store"].role_assignments)

    team_id = sql_store_with_team["default_team"].id
    new_role = RoleRequestModel(
        name="blupus_friend", permissions={PermissionType.ME}
    )
    sql_store["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("blupus_friend").id)
    sql_store["store"].assign_role(new_role_id, team_id, is_user=False)
    sql_store["store"].revoke_role(new_role_id, team_id, is_user=False)

    assert len(sql_store_with_team["store"].roles) == roles_before + 1
    assert (
        len(sql_store_with_team["store"].role_assignments)
        == role_assignments_before
    )


def test_revoking_nonexistent_role_fails(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a nonexistent role fails."""
    current_user_id = sql_store_with_team["active_user"].id
    with pytest.raises(KeyError):
        sql_store["store"].revoke_role(uuid.uuid4(), current_user_id)


def test_revoking_role_for_nonexistent_user_fails(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a nonexistent user fails."""
    new_role = RoleRequestModel(
        name="aria_feeder", permissions={PermissionType.ME}
    )
    sql_store["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    current_user_id = sql_store_with_team["active_user"].id
    sql_store["store"].assign_role(new_role_id, current_user_id)
    with pytest.raises(KeyError):
        sql_store["store"].revoke_role(new_role_id, uuid.uuid4())


#  .----------------.
# | METADATA_CONFIG |
# '-----------------'


def test_get_metadata_config_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting metadata config."""
    metadata_config = sql_store["store"].get_metadata_config()
    assert metadata_config is not None


#  .-------.
# | STACKS |
# '--------'


def test_list_stacks_succeeds(
    sql_store: BaseZenStore,
):
    """Tests listing stacks."""
    assert len(sql_store["store"].list_stacks()) == 1


def test_list_stacks_fails_with_nonexistent_project(
    sql_store: BaseZenStore,
):
    """Tests listing stacks fails with nonexistent project."""
    with pytest.raises(KeyError):
        sql_store["store"].list_stacks(project_name_or_id=uuid.uuid4())


def test_get_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting stack."""
    current_stack_id = sql_store["store"].list_stacks()[0].id
    stack = sql_store["store"].get_stack(stack_id=current_stack_id)
    assert stack is not None


def test_get_stack_fails_with_nonexistent_stack_id(
    sql_store: BaseZenStore,
):
    """Tests getting stack fails with nonexistent stack id."""
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(uuid.uuid4())


def test_register_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests registering stack."""
    new_stack = StackRequestModel(
        name="arias_stack",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    # TODO: [server] inject user and project into stack as well
    sql_store["store"].create_stack(
        stack=new_stack,
    )
    stacks = sql_store["store"].list_stacks(DEFAULT_NAME)
    assert len(stacks) == 2
    assert sql_store["store"].get_stack(stacks[0].id) is not None


def test_register_stack_fails_when_stack_exists(
    sql_store: BaseZenStore,
):
    """Tests registering stack fails when stack exists."""
    new_stack = StackRequestModel(
        name=DEFAULT_NAME,
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with pytest.raises(StackExistsError):
        # TODO: [server] inject user and project into stack as well
        sql_store["store"].create_stack(
            stack=new_stack,
        )


def test_updating_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests updating stack."""
    new_stack = StackRequestModel(
        name="arias_stack",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    new_stack = sql_store["store"].create_stack(
        stack=new_stack,
    )
    new_stack_name = "axls_stack"
    stack_update = StackUpdateModel(name=new_stack_name)
    sql_store["store"].update_stack(stack_id=new_stack.id,
                                    stack_update=stack_update)
    assert sql_store["store"].get_stack(new_stack.id) is not None
    assert sql_store["store"].get_stack(new_stack.id).name == new_stack_name
    # Ensure unset fields of the UpdateModel are not changed
    assert sql_store["store"].get_stack(new_stack.id).active == new_stack.active


def test_updating_default_stack_fails(
    sql_store: BaseZenStore,
):
    """Tests that updating the default stack is prohibited."""
    default_stack_id = sql_store["default_stack"].id
    default_stack = sql_store["store"].get_stack(default_stack_id)
    default_stack.name = "axl"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack(default_stack)


def test_updating_nonexistent_stack_fails(
    sql_store: BaseZenStore,
):
    """Tests updating nonexistent stack fails."""
    current_stack_id = sql_store["default_stack"].id
    new_stack = StackRequestModel(
        name="arias_stack",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_stack(new_stack)
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(new_stack.id)
    assert sql_store["store"].get_stack(current_stack_id).name != "arias_stack"


def test_deleting_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting stack."""
    new_stack = StackRequestModel(
        name="arias_stack",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    new_stack = sql_store["store"].create_stack(
        stack=new_stack,
    )
    sql_store["store"].delete_stack(new_stack.id)
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(new_stack.id)


def test_deleting_default_stack_fails(
    sql_store: BaseZenStore,
):
    """Tests that deleting the default stack is prohibited."""
    default_stack_id = sql_store["default_stack"].id
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_stack(default_stack_id)


def test_deleting_nonexistent_stack_fails(
    sql_store: BaseZenStore,
):
    """Tests deleting nonexistent stack fails."""
    non_existent_stack_id = uuid.uuid4()
    with pytest.raises(KeyError):
        sql_store["store"].delete_stack(non_existent_stack_id)


def test_deleting_a_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting stack."""
    # TODO: [server] inject user and project into stack as well
    new_stack = StackRequestModel(
        name="arias_stack",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    sql_store["store"].create_stack(
        stack=new_stack,
    )
    stacks = sql_store["store"].list_stacks(project_name_or_id=DEFAULT_NAME)
    assert len(stacks) == 2
    new_stack = [stack for stack in stacks if stack.name == "arias_stack"][0]
    sql_store["store"].delete_stack(new_stack.id)
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(new_stack.id)


# ------------
# TFX Metadata
# ------------


def test_tfx_metadata_succeeds(
    sql_store: BaseZenStore,
):
    """Tests tfx metadata."""
    with does_not_raise():
        config = sql_store["store"].get_metadata_config()
        assert config is not None
        assert type(config) == ConnectionConfig


# ---------
# Pipelines
# ---------


def test_create_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests creating pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipelines = sql_store["store"].list_pipelines()
    assert len(pipelines) == 1
    assert pipelines[0].name == "arias_pipeline"


def test_creating_identical_pipeline_fails(
    sql_store: BaseZenStore,
):
    """Tests creating identical pipeline fails."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipelines = sql_store["store"].list_pipelines()
    assert len(pipelines) == 1


def test_get_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    pipeline = sql_store["store"].get_pipeline(name_id_or_prefix=pipeline_id)
    assert pipeline is not None
    assert pipeline.name == "arias_pipeline"


def test_get_pipeline_fails_for_nonexistent_pipeline(
    sql_store: BaseZenStore,
):
    """Tests getting pipeline fails for nonexistent pipeline."""
    with pytest.raises(KeyError):
        sql_store["store"].get_pipeline(uuid.uuid4())


def test_get_pipeline_in_project_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting pipeline in project."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline = sql_store["store"].get_pipeline_in_project(
        project_name_or_id=project_id, pipeline_name="arias_pipeline"
    )
    assert pipeline is not None
    assert pipeline.name == "arias_pipeline"


def test_get_pipeline_in_project_fails_when_pipeline_nonexistent(
    sql_store: BaseZenStore,
):
    """Tests getting pipeline in project fails when pipeline nonexistent."""
    project_id = sql_store["default_project"].id
    with pytest.raises(KeyError):
        sql_store["store"].get_pipeline_in_project(
            project_name_or_id=project_id, pipeline_name="blupus_ka_pipeline"
        )


def test_list_pipelines_succeeds(
    sql_store: BaseZenStore,
):
    """Tests listing pipelines."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    with does_not_raise():
        pipelines = sql_store["store"].list_pipelines()
        assert len(pipelines) == 1


def test_update_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests updating pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    updated_pipeline = PipelineModel(
        id=pipeline_id,
        name="blupus_ka_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].update_pipeline(updated_pipeline)
    pipeline = sql_store["store"].get_pipeline(pipeline_id)
    assert pipeline is not None
    assert pipeline.name == "blupus_ka_pipeline"


def test_updating_nonexistent_pipeline_fails(
    sql_store: BaseZenStore,
):
    """Tests updating nonexistent pipeline fails."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    updated_pipeline = PipelineModel(
        name="blupus_ka_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_pipeline(pipeline=updated_pipeline)


def test_deleting_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    sql_store["store"].delete_pipeline(pipeline_id)
    assert len(sql_store["store"].list_pipelines()) == 0
    with pytest.raises(KeyError):
        sql_store["store"].get_pipeline(pipeline_id)


def test_deleting_nonexistent_pipeline_fails(
    sql_store: BaseZenStore,
):
    """Tests deleting nonexistent pipeline fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_pipeline(uuid.uuid4())


# --------------
# Pipeline runs
# --------------


def test_getting_run_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run."""
    run_id = sql_store_with_run["pipeline_run"].id
    with does_not_raise():
        run = sql_store_with_run["store"].get_run(run_id)
        assert run is not None
        assert run.name == sql_store_with_run["pipeline_run"].name


def test_getting_nonexistent_run_fails(
    sql_store: BaseZenStore,
):
    """Tests getting nonexistent run fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run(uuid.uuid4())


def test_list_runs_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests listing runs."""
    run = sql_store_with_run["pipeline_run"]
    with does_not_raise():
        runs = sql_store_with_run["store"].list_runs()
        assert len(runs) == 1
        assert runs[0].name == run.name


def test_list_runs_returns_nothing_when_no_runs_exist(
    sql_store: BaseZenStore,
):
    """Tests listing runs returns nothing when no runs exist."""
    runs = sql_store["store"].list_runs()
    assert len(runs) == 0

    with pytest.raises(KeyError):
        sql_store["store"].list_runs(project_name_or_id=uuid.uuid4())

    false_stack_runs = sql_store["store"].list_runs(stack_id=uuid.uuid4())
    assert len(false_stack_runs) == 0

    false_run_name_runs = sql_store["store"].list_runs(run_name="not_arias_run")
    assert len(false_run_name_runs) == 0

    with pytest.raises(KeyError):
        sql_store["store"].list_runs(user_name_or_id=uuid.uuid4())

    false_pipeline_runs = sql_store["store"].list_runs(pipeline_id=uuid.uuid4())
    assert len(false_pipeline_runs) == 0


def test_list_runs_is_ordered(sql_store_with_runs):
    """Tests listing runs returns ordered runs."""
    runs = sql_store_with_runs["store"].list_runs()
    assert len(runs) == 10
    assert all(
        runs[i].created <= runs[i + 1].created for i in range(len(runs) - 1)
    )


# ------------------
# Pipeline run steps
# ------------------


def test_get_run_step_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step."""
    pipeline_step = sql_store_with_run["step"]
    run_step = sql_store_with_run["store"].get_run_step(
        step_id=pipeline_step.id
    )
    assert run_step is not None
    assert run_step.id == pipeline_step.id
    assert run_step == pipeline_step


def test_get_run_step_fails_when_step_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests getting run step fails when step does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run_step(step_id=uuid.uuid4())


def test_get_run_step_outputs_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step outputs."""
    pipeline_step = sql_store_with_run["step"]
    run_step_outputs = sql_store_with_run["store"].list_artifacts(
        parent_step_id=pipeline_step.id
    )
    assert len(run_step_outputs) == 1


def test_get_run_step_inputs_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step inputs."""
    pipeline_step = sql_store_with_run["step"]
    run_step_inputs = sql_store_with_run["store"].get_run_step_inputs(
        step_id=pipeline_step.id
    )
    assert len(run_step_inputs) == 1


def test_get_run_step_inputs_fails_when_step_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests getting run step inputs fails when step does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run_step_inputs(step_id=uuid.uuid4())


def test_get_run_step_status_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step status."""
    pipeline_step = sql_store_with_run["step"]
    run_step_status = (
        sql_store_with_run["store"]
        .get_run_step(step_id=pipeline_step.id)
        .status
    )
    assert run_step_status is not None
    assert isinstance(run_step_status, ExecutionStatus)
    assert run_step_status == ExecutionStatus.COMPLETED


def test_list_run_steps_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests listing run steps."""
    run_steps = sql_store_with_run["store"].list_run_steps(
        run_id=sql_store_with_run["pipeline_run"].id
    )
    assert len(run_steps) == 2
    assert run_steps[1] == sql_store_with_run["step"]


# ----------------
# Stack components
# ----------------


def test_create_stack_component_succeeds(
    sql_store: BaseZenStore,
):
    """Tests creating stack component."""
    stack_component_name = "arias_cat_detection_orchestrator"
    stack_component = ComponentRequestModel(
        name=stack_component_name,
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        created_component = sql_store["store"].create_stack_component(
            component=stack_component
        )
        assert created_component.name == stack_component_name


def test_create_component_fails_when_same_name(
    sql_store: BaseZenStore,
):
    """Tests creating component fails when same name."""
    stack_component_name = "nicto"
    stack_component = ComponentRequestModel(
        name=stack_component_name,
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    sql_store["store"].create_stack_component(component=stack_component)
    with pytest.raises(StackComponentExistsError):
        sql_store["store"].create_stack_component(component=stack_component)


def test_get_stack_component(
    sql_store: BaseZenStore,
):
    """Tests getting stack component."""
    components = sql_store["default_stack"].components
    component_id = list(components.values())[0][0].id
    with does_not_raise():
        sql_store["store"].get_stack_component(component_id=component_id)


def test_get_stack_component_fails_when_component_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests getting stack component fails when component does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_stack_component(component_id=uuid.uuid4())


def test_list_stack_components_succeeds(
    sql_store: BaseZenStore,
):
    """Tests listing stack components."""
    stack_components = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name
    )
    assert len(stack_components) == 2
    component_types = [component.type for component in stack_components]
    assert StackComponentType.ORCHESTRATOR in component_types
    assert StackComponentType.ARTIFACT_STORE in component_types


def test_list_stack_components_fails_when_project_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests listing stack components fails when project does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].list_stack_components(
            project_name_or_id=uuid.uuid4()
        )


def test_list_stack_components_works_with_filters(
    sql_store: BaseZenStore,
):
    """Tests listing stack components works with filters."""
    artifact_stores = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ARTIFACT_STORE,
    )
    assert len(artifact_stores) == 1
    assert artifact_stores[0].type == StackComponentType.ARTIFACT_STORE

    orchestrators = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ORCHESTRATOR,
    )
    assert len(orchestrators) == 1
    assert orchestrators[0].type == StackComponentType.ORCHESTRATOR


def test_list_stack_components_lists_nothing_for_nonexistent_filters(
    sql_store: BaseZenStore,
):
    """Tests listing stack components lists nothing for nonexistent filters."""
    flavor_filtered = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        flavor_name="nonexistent",
    )
    assert len(flavor_filtered) == 0

    with pytest.raises(KeyError):
        sql_store["store"].list_stack_components(
            project_name_or_id=sql_store["default_project"].name,
            user_name_or_id=uuid.uuid4(),
        )

    name_filtered = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        name="nonexistent",
    )
    assert len(name_filtered) == 0


def test_update_stack_component_succeeds(
    sql_store: BaseZenStore,
):
    """Tests updating stack component."""
    stack_component_name = "aria"
    stack_component = ComponentRequestModel(
        name=stack_component_name,
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        orchestrator = sql_store["store"].create_stack_component(
            component=stack_component
        )

    updated_orchestrator_name = "axl"
    orchestrator.name = updated_orchestrator_name
    with does_not_raise():
        sql_store["store"].update_stack_component(component=orchestrator)
        updated_stack_component = sql_store["store"].get_stack_component(
            component_id=orchestrator.id
        )
        assert updated_stack_component.name == updated_orchestrator_name


def test_update_default_stack_component_fails(
    sql_store: BaseZenStore,
):
    """Tests that updating default stack components fails."""
    default_artifact_store = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ARTIFACT_STORE,
        name="default",
    )[0]

    default_orchestrator = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ORCHESTRATOR,
        name="default",
    )[0]

    default_artifact_store.name = "aria"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack_component(
            component=default_artifact_store
        )

    default_orchestrator.name = "axl"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack_component(
            component=default_orchestrator
        )


def test_update_stack_component_fails_when_component_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests updating stack component fails when component does not exist."""
    stack_component = ComponentRequestModel(
        name="nonexistent",
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_stack_component(component=stack_component)


def test_delete_stack_component_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting stack component."""
    stack_component_name = "arias_cat_detection_orchestrator"
    stack_component = ComponentRequestModel(
        name=stack_component_name,
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    created_component = sql_store["store"].create_stack_component(
        component=stack_component
    )
    print(created_component.name)
    created_stack_component_id = (
        sql_store["store"]
        .get_stack_component(component_id=created_component.id)
        .id
    )
    orchestrators = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ORCHESTRATOR,
    )
    assert len(orchestrators) == 2
    with does_not_raise():
        sql_store["store"].delete_stack_component(
            component_id=created_stack_component_id
        )
        orchestrators = sql_store["store"].list_stack_components(
            project_name_or_id=sql_store["default_project"].name,
            type=StackComponentType.ORCHESTRATOR,
        )
        assert len(orchestrators) == 1
    with pytest.raises(KeyError):
        assert sql_store["store"].get_stack_component(
            component_id=created_component.id
        )


def test_delete_default_stack_component_fails(
    sql_store: BaseZenStore,
):
    """Tests that deleting default stack components is prohibited."""
    default_artifact_store = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ARTIFACT_STORE,
        name="default",
    )[0]

    default_orchestrator = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ORCHESTRATOR,
        name="default",
    )[0]

    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_stack_component(default_artifact_store.id)

    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_stack_component(default_orchestrator.id)


def test_delete_stack_component_fails_when_component_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests deleting stack component fails when component does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_stack_component(component_id=uuid.uuid4())


# -----------------------
# Stack component flavors
# -----------------------


def test_create_stack_component_flavor_succeeds(
    sql_store: BaseZenStore,
):
    """Tests creating stack component flavor."""
    flavor_name = "blupus"
    blupus_flavor = FlavorRequestModel(
        name=flavor_name,
        type=StackComponentType.ORCHESTRATOR,
        config_schema="default",
        source=".",
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        sql_store["store"].create_flavor(flavor=blupus_flavor)
        blupus_flavor_id = (
            sql_store["store"]
            .list_flavors(
                project_name_or_id=sql_store["default_project"].name,
                component_type=StackComponentType.ORCHESTRATOR,
                name=flavor_name,
            )[0]
            .id
        )
        created_flavor = sql_store["store"].get_flavor(
            flavor_id=blupus_flavor_id
        )
        assert created_flavor.name == flavor_name


def test_create_stack_component_fails_when_flavor_already_exists(
    sql_store: BaseZenStore,
):
    """Tests creating stack component flavor fails when flavor already exists."""
    flavor_name = "scinda"
    scinda_flavor = FlavorRequestModel(
        name=flavor_name,
        type=StackComponentType.ORCHESTRATOR,
        config_schema="default",
        source=".",
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        sql_store["store"].create_flavor(flavor=scinda_flavor)
    scinda_copy_flavor = FlavorRequestModel(
        name=flavor_name,
        type=StackComponentType.ORCHESTRATOR,
        config_schema="default",
        source=".",
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_flavor(flavor=scinda_copy_flavor)


def test_get_flavor_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting stack component flavor."""
    flavor_name = "verata"
    verata_flavor = FlavorRequestModel(
        name=flavor_name,
        type=StackComponentType.ARTIFACT_STORE,
        config_schema="default",
        source=".",
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        sql_store["store"].create_flavor(flavor=verata_flavor)
        verata_flavor_id = (
            sql_store["store"]
            .list_flavors(
                project_name_or_id=sql_store["default_project"].name,
                component_type=StackComponentType.ARTIFACT_STORE,
                name=flavor_name,
            )[0]
            .id
        )
        assert (
            sql_store["store"].get_flavor(flavor_id=verata_flavor_id).name
            == flavor_name
        )


def test_get_flavor_fails_when_flavor_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests getting stack component flavor fails when flavor does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_flavor(flavor_id=uuid.uuid4())


def test_list_flavors_succeeds(
    sql_store: BaseZenStore,
):
    """Tests listing stack component flavors."""
    flavor_name = "verata"
    verata_flavor = FlavorRequestModel(
        name=flavor_name,
        type=StackComponentType.ARTIFACT_STORE,
        config_schema="default",
        source=".",
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with does_not_raise():
        sql_store["store"].create_flavor(flavor=verata_flavor)
        assert len(sql_store["store"].list_flavors()) == 1
        assert sql_store["store"].list_flavors()[0].name == flavor_name


def test_list_flavors_fails_with_nonexistent_project(
    sql_store: BaseZenStore,
):
    """Tests listing stack component flavors fails with nonexistent project."""
    with pytest.raises(KeyError):
        sql_store["store"].list_flavors(
            project_name_or_id="nonexistent",
            component_type=StackComponentType.ORCHESTRATOR,
        )
