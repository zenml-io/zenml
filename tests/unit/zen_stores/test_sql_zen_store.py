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

import json
import uuid
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.exceptions import EntityExistsError, StackExistsError
from zenml.models import ProjectModel, RoleModel, TeamModel, UserModel
from zenml.models.pipeline_models import PipelineModel, PipelineRunModel
from zenml.models.stack_models import StackModel
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.user_management_schemas import (
    RoleSchema,
    TeamSchema,
    UserSchema,
)

DEFAULT_NAME = "default"

#  .--------
# | PROJECTS
# '---------


def test_only_one_default_project(sql_store: BaseZenStore):
    """Tests that only one default project can be created."""
    assert len(sql_store["store"].list_projects()) == 1


def test_project_creation(sql_store: BaseZenStore):
    """Tests project creation."""
    new_project = ProjectModel(name="arias_project")
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


def test_updating_project(sql_store: BaseZenStore):
    """Tests updating a project."""
    default_project = sql_store["default_project"]
    assert default_project.name == DEFAULT_NAME
    default_project.name = "aria"
    sql_store["store"].update_project(DEFAULT_NAME, default_project)
    assert sql_store["store"].list_projects()[0].name == "aria"


def test_updating_nonexisting_project_raises_error(
    sql_store: BaseZenStore,
):
    """Tests updating a nonexistent project raises an error."""
    new_project = ProjectModel(name="arias_project")
    with pytest.raises(KeyError):
        sql_store["store"].update_project("blupus_project", new_project)


def test_deleting_project_succeeds(sql_store: BaseZenStore):
    """Tests deleting a project."""
    sql_store["store"].delete_project(DEFAULT_NAME)
    assert len(sql_store["store"].list_projects()) == 0


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
    new_team = TeamModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert len(sql_store["store"].teams) == 1
    assert sql_store["store"].teams[0].name == "arias_team"


def test_get_team(sql_store: BaseZenStore):
    """Tests getting a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert sql_store["store"].get_team("arias_team").name == "arias_team"


def test_get_nonexistent_team_raises_error(sql_store: BaseZenStore):
    """Tests getting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_team("blupus_team")


def test_delete_team_works(sql_store: BaseZenStore):
    """Tests deleting a team."""
    assert len(sql_store["store"].teams) == 0
    new_team = TeamModel(name="arias_team")
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
    new_team = TeamModel(name=team_name)
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
    new_team = TeamModel(name="arias_team")
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
    new_team = TeamModel(name="arias_team")
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
    new_team = TeamModel(name="arias_team")
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
    new_team = TeamModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    new_team_id = sql_store["store"].get_team("arias_team").id
    sql_store["store"].add_user_to_team(current_user_id, new_team_id)
    users_for_team = sql_store["store"].get_users_for_team(new_team_id)
    assert len(users_for_team) == 1
    assert users_for_team[0].id == current_user_id


def test_getting_team_for_user(sql_store: BaseZenStore):
    """Tests getting a team for a user."""
    new_team = TeamModel(name="arias_team")
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
    new_user = UserModel(name="aria")
    sql_store["store"].create_user(new_user)
    assert len(sql_store["store"].users) == 2
    assert sql_store["store"].get_user("aria") is not None


def test_creating_user_with_existing_name_fails(
    sql_store: BaseZenStore,
):
    """Tests creating a user with an existing name fails."""
    new_user = UserModel(name="aria")
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
    new_user = UserModel(name="aria")
    sql_store["store"].create_user(new_user)
    users = sql_store["store"].users
    new_user_id = str(users[1].id)
    user_by_name = sql_store["store"].get_user("aria")
    user_by_id = sql_store["store"].get_user(new_user_id)
    assert user_by_id == user_by_name
    assert len(users) == 2


def test_updating_user_succeeds(sql_store: BaseZenStore):
    """Tests updating a user."""
    new_user_model = UserModel(name="aria")
    sql_store["store"].create_user(new_user_model)
    new_user = sql_store["store"].get_user("aria")
    new_user.name = "blupus"
    sql_store["store"].update_user(new_user.id, new_user)
    assert sql_store["store"].get_user("blupus") is not None
    with pytest.raises(KeyError):
        sql_store["store"].get_user("aria")


def test_updating_nonexistent_user_fails(sql_store: BaseZenStore):
    """Tests updating a nonexistent user fails."""
    new_user = UserModel(name="demonic_aria")
    with pytest.raises(KeyError):
        sql_store["store"].update_user(uuid.uuid4(), new_user)


def test_deleting_user_succeeds(sql_store: BaseZenStore):
    """Tests deleting a user."""
    new_user = UserModel(name="aria")
    sql_store["store"].create_user(new_user)
    new_user_id = sql_store["store"].get_user("aria").id
    assert len(sql_store["store"].users) == 2
    sql_store["store"].delete_user(new_user_id)
    assert len(sql_store["store"].users) == 1


#  .------.
# | ROLES |
# '-------'


def test_roles_property_with_fresh_store(sql_store: BaseZenStore):
    """Tests the roles property with a fresh ZenStore."""
    assert len(sql_store["store"].roles) == 0


def test_creating_role(sql_store: BaseZenStore):
    """Tests creating a role."""
    assert len(sql_store["store"].roles) == 0
    new_role = RoleModel(name="admin")
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == 1
    assert sql_store["store"].get_role("admin") is not None


def test_creating_existing_role_fails(sql_store: BaseZenStore):
    """Tests creating an existing role fails."""
    new_role = RoleModel(name="admin")
    sql_store["store"].create_role(new_role)
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == 1


def test_getting_role_succeeds(sql_store: BaseZenStore):
    """Tests getting a role."""
    new_role = RoleModel(name="admin")
    sql_store["store"].create_role(new_role)
    assert sql_store["store"].get_role("admin") is not None


def test_getting_nonexistent_role_fails(sql_store: BaseZenStore):
    """Tests getting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_role("admin")


def test_deleting_role_succeeds(sql_store: BaseZenStore):
    """Tests deleting a role."""
    new_role = RoleModel(name="admin")
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == 1
    new_role_id = str(sql_store["store"].get_role("admin").id)
    sql_store["store"].delete_role(new_role_id)
    assert len(sql_store["store"].roles) == 0
    with pytest.raises(KeyError):
        sql_store["store"].get_role(new_role_id)


def test_deleting_nonexistent_role_fails(sql_store: BaseZenStore):
    """Tests deleting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_role(uuid.uuid4())


#  .----------------
# | ROLE ASSIGNMENTS
# '-----------------


def test_assigning_role_to_user_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = sql_store_with_team["active_user"].id

    sql_store_with_team["store"].create_role(new_role)
    new_role_id = sql_store_with_team["store"].get_role("aria_feeder").id
    sql_store_with_team["store"].assign_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == 1
    assert len(sql_store_with_team["store"].role_assignments) == 1


def test_assigning_role_to_team_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a team."""
    team_id = sql_store_with_team["default_team"].id
    new_role = RoleModel(name="blupus_friend")
    sql_store_with_team["store"].create_role(new_role)
    new_role_id = sql_store_with_team["store"].get_role("blupus_friend").id
    sql_store_with_team["store"].assign_role(
        new_role_id, team_id, is_user=False
    )

    assert len(sql_store_with_team["store"].roles) == 1
    assert len(sql_store_with_team["store"].role_assignments) == 1
    assert (
        len(
            sql_store_with_team["store"].list_role_assignments(
                user_name_or_id=sql_store_with_team["active_user"].id
            )
        )
        == 1
    )


def test_assigning_role_if_assignment_already_exists(
    sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user if the assignment already exists."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = sql_store_with_team["active_user"].id
    sql_store_with_team["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    sql_store_with_team["store"].assign_role(new_role_id, current_user_id)
    with pytest.raises(EntityExistsError):
        sql_store_with_team["store"].assign_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == 1
    assert len(sql_store_with_team["store"].role_assignments) == 1


def test_revoking_role_for_user_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a user."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = sql_store_with_team["active_user"].id
    sql_store_with_team["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    sql_store_with_team["store"].assign_role(new_role_id, current_user_id)
    sql_store_with_team["store"].revoke_role(new_role_id, current_user_id)

    assert len(sql_store_with_team["store"].roles) == 1
    assert len(sql_store_with_team["store"].role_assignments) == 0


def test_revoking_role_for_team_succeeds(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a team."""
    team_id = sql_store_with_team["default_team"].id
    new_role = RoleModel(name="blupus_friend")
    sql_store_with_team["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("blupus_friend").id)
    sql_store_with_team["store"].assign_role(
        new_role_id, team_id, is_user=False
    )
    sql_store_with_team["store"].revoke_role(
        new_role_id, team_id, is_user=False
    )

    assert len(sql_store_with_team["store"].roles) == 1
    assert len(sql_store_with_team["store"].role_assignments) == 0


def test_revoking_nonexistent_role_fails(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a nonexistent role fails."""
    current_user_id = sql_store_with_team["active_user"].id
    with pytest.raises(KeyError):
        sql_store_with_team["store"].revoke_role(uuid.uuid4(), current_user_id)


def test_revoking_role_for_nonexistent_user_fails(
    sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a nonexistent user fails."""
    new_role = RoleModel(name="aria_feeder")
    sql_store_with_team["store"].create_role(new_role)
    new_role_id = str(sql_store_with_team["store"].get_role("aria_feeder").id)
    current_user_id = sql_store_with_team["active_user"].id
    sql_store_with_team["store"].assign_role(new_role_id, current_user_id)
    with pytest.raises(KeyError):
        sql_store_with_team["store"].revoke_role(new_role_id, uuid.uuid4())


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


# TODO: remove `xfail` when we raise the error again
@pytest.mark.xfail
def test_list_stacks_fails_with_nonexistent_project(
    sql_store: BaseZenStore,
):
    """Tests listing stacks fails with nonexistent project."""
    with pytest.raises(KeyError):
        sql_store["store"].list_stacks(uuid.uuid4())


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
    new_stack = StackModel(name="arias_stack", components={})
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
    new_stack = StackModel(name=DEFAULT_NAME, components={})
    with pytest.raises(StackExistsError):
        # TODO: [server] inject user and project into stack as well
        sql_store["store"].create_stack(
            stack=new_stack,
        )


def test_updating_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests updating stack."""
    current_stack_id = sql_store["default_stack"].id
    new_stack = StackModel(
        id=current_stack_id, name="arias_stack", components={}
    )
    sql_store["store"].update_stack(new_stack)
    assert sql_store["store"].get_stack(current_stack_id) is not None
    assert sql_store["store"].get_stack(current_stack_id).name == "arias_stack"


def test_updating_nonexistent_stack_fails(
    sql_store: BaseZenStore,
):
    """Tests updating nonexistent stack fails."""
    current_stack_id = sql_store["default_stack"].id
    new_stack = StackModel(name="arias_stack", components={})
    non_existent_stack_id = uuid.uuid4()
    with pytest.raises(KeyError):
        new_stack.id = non_existent_stack_id
        sql_store["store"].update_stack(new_stack)
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(non_existent_stack_id)
    assert sql_store["store"].get_stack(current_stack_id).name != "arias_stack"


def test_deleting_default_stack_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting stack."""
    current_stack_id = sql_store["default_stack"].id
    sql_store["store"].delete_stack(current_stack_id)
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(current_stack_id)


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
    new_stack = StackModel(name="arias_stack", components={})
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
    config = sql_store["store"].get_metadata_config()
    assert config is not None
    assert type(config) == str
    try:
        json_config = json.loads(config)
        assert json_config is not None
        assert type(json_config) == dict
    except json.JSONDecodeError:
        assert False


# =======================
# Internal helper methods
# =======================


def test_get_schema_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting schema."""
    schema = sql_store["store"]._get_schema_by_name_or_id(
        DEFAULT_NAME, ProjectSchema, "project"
    )
    assert schema is not None
    assert type(schema) == ProjectSchema


def test_get_schema_fails_for_nonexistent_object(
    sql_store: BaseZenStore,
):
    """Tests getting schema fails for nonexistent object."""
    with pytest.raises(KeyError):
        sql_store["store"]._get_schema_by_name_or_id(
            "arias_project", ProjectSchema, "project"
        )


def test_get_project_schema_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting project schema."""
    schema = sql_store["store"]._get_project_schema(DEFAULT_NAME)
    assert schema is not None
    assert type(schema) == ProjectSchema


def test_get_user_schema_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting user schema."""
    schema = sql_store["store"]._get_user_schema(DEFAULT_NAME)
    assert schema is not None
    assert type(schema) == UserSchema


def test_get_team_schema_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting team schema."""
    new_team = TeamModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    schema = sql_store["store"]._get_team_schema("arias_team")
    assert schema is not None
    assert type(schema) == TeamSchema


def test_get_role_schema_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting role schema."""
    new_role = RoleModel(name="aria_admin")
    sql_store["store"].create_role(new_role)
    schema = sql_store["store"]._get_role_schema("aria_admin")
    assert schema is not None
    assert type(schema) == RoleSchema


# ---------
# Pipelines
# ---------


def test_create_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests creating pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
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
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
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
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    pipeline = sql_store["store"].get_pipeline(pipeline_id=pipeline_id)
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
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
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
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
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
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    updated_pipeline = PipelineModel(
        name="blupus_ka_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
    )
    sql_store["store"].update_pipeline(
        pipeline_id=pipeline_id,
        pipeline=updated_pipeline,
    )
    pipeline = sql_store["store"].get_pipeline(pipeline_id)
    assert pipeline is not None
    assert pipeline.name == "blupus_ka_pipeline"


def test_updating_nonexistent_pipeline_fails(
    sql_store: BaseZenStore,
):
    """Tests updating nonexistent pipeline fails."""
    project_id = sql_store["default_project"].id
    owner_id = sql_store["active_user"].id
    updated_pipeline = PipelineModel(
        name="blupus_ka_pipeline",
        project_id=project_id,
        owner=owner_id,
        configuration={},
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_pipeline(
            pipeline_id=uuid.uuid4(),
            pipeline=updated_pipeline,
        )


def test_deleting_pipeline_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    new_pipeline = PipelineModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        configuration={},
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


def test_create_pipeline_run_succeeds(
    sql_store: BaseZenStore,
):
    """Tests creating pipeline run."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    with does_not_raise():
        sql_store["store"].create_run(pipeline_run=pipeline_run)


def test_creating_pipeline_run_fails_when_run_already_exists(
    sql_store: BaseZenStore,
):
    """Tests creating pipeline run fails when run already exists."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_run(pipeline_run=pipeline_run)


def test_creating_pipeline_run_fails_when_no_pipeline_exists(
    sql_store: BaseZenStore,
):
    """Tests creating pipeline run fails when no pipeline exists."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
        pipeline_id=uuid.uuid4(),
    )
    with pytest.raises(KeyError):
        sql_store["store"].create_run(pipeline_run=pipeline_run)


def test_getting_run_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting run."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)
    run_id = sql_store["store"].list_runs()[0].id
    with does_not_raise():
        run = sql_store["store"].get_run(run_id=run_id)
        assert run is not None
        assert run.name == "arias_pipeline_run"


def test_getting_nonexistent_run_fails(
    sql_store: BaseZenStore,
):
    """Tests getting nonexistent run fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run(uuid.uuid4())


# TODO: remove `xfail` once the method is properly implemented
@pytest.mark.xfail
def test_get_run_in_project_succeeds(
    sql_store: BaseZenStore,
):
    """Tests getting run in project."""
    run_name = "arias_pipeline_run"
    pipeline_run = PipelineRunModel(
        name=run_name,
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)

    with does_not_raise():
        run = sql_store["store"].get_run_in_project(
            run_name=run_name, project_name_or_id=DEFAULT_NAME
        )
        assert run is not None
        assert run.name == "arias_pipeline_run"


def test_get_run_in_project_fails_for_nonexistent_run(
    sql_store: BaseZenStore,
):
    """Tests getting run in project fails for nonexistent run."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run_in_project(
            run_name="nonexistent_run", project_name_or_id=DEFAULT_NAME
        )


def test_list_runs_succeeds(
    sql_store: BaseZenStore,
):
    """Tests listing runs."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)
    with does_not_raise():
        runs = sql_store["store"].list_runs()
        assert len(runs) == 1
        assert runs[0].name == "arias_pipeline_run"


def test_list_runs_returns_nothing_when_no_runs_exist(
    sql_store: BaseZenStore,
):
    """Tests listing runs returns nothing when no runs exist."""
    runs = sql_store["store"].list_runs()
    assert len(runs) == 0

    false_project_runs = sql_store["store"].list_runs(
        project_name_or_id=uuid.uuid4()
    )
    assert len(false_project_runs) == 0

    false_stack_runs = sql_store["store"].list_runs(stack_id=uuid.uuid4())
    assert len(false_stack_runs) == 0

    false_run_name_runs = sql_store["store"].list_runs(run_name="not_arias_run")
    assert len(false_run_name_runs) == 0

    false_user_runs = sql_store["store"].list_runs(user_name_or_id=uuid.uuid4())
    assert len(false_user_runs) == 0

    false_pipeline_runs = sql_store["store"].list_runs(pipeline_id=uuid.uuid4())
    assert len(false_pipeline_runs) == 0


def test_update_run_succeeds(
    sql_store: BaseZenStore,
):
    """Tests updating run."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)
    run_id = sql_store["store"].list_runs()[0].id
    run = sql_store["store"].get_run(run_id=run_id)
    run.name = "updated_arias_run"
    with does_not_raise():
        sql_store["store"].update_run(run=run)
        updated_run = sql_store["store"].get_run(run_id=run_id)
        assert updated_run.name == "updated_arias_run"


def test_update_run_fails_when_run_does_not_exist(
    sql_store: BaseZenStore,
):
    """Tests updating run fails when run does not exist."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_run(run=pipeline_run)


def test_delete_run_succeeds(
    sql_store: BaseZenStore,
):
    """Tests deleting run."""
    pipeline_run = PipelineRunModel(
        name="arias_pipeline_run",
    )
    sql_store["store"].create_run(pipeline_run=pipeline_run)
    run_id = sql_store["store"].list_runs()[0].id
    with does_not_raise():
        sql_store["store"].delete_run(run_id=run_id)
        assert len(sql_store["store"].list_runs()) == 0
    with pytest.raises(KeyError):
        sql_store["store"].get_run(run_id=run_id)
