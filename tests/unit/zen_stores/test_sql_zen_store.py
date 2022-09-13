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

import pytest

from zenml.exceptions import EntityExistsError, StackExistsError
from zenml.models import ProjectModel, RoleModel, TeamModel, UserModel
from zenml.models.stack_models import StackModel
from zenml.zen_stores.base_zen_store import BaseZenStore

#  .--------
# | PROJECTS
# '---------


def test_only_one_default_project(fresh_sql_zen_store: BaseZenStore):
    """Tests that only one default project can be created."""
    assert len(fresh_sql_zen_store.list_projects()) == 1


def test_project_creation(fresh_sql_zen_store: BaseZenStore):
    """Tests project creation."""
    new_project = ProjectModel(name="arias_project")
    fresh_sql_zen_store.create_project(new_project)
    projects_list = fresh_sql_zen_store.list_projects()
    assert len(projects_list) == 2
    assert projects_list[1].name == "arias_project"


def test_getting_project(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a project."""
    default_project = fresh_sql_zen_store.get_project("default")
    assert default_project.name == "default"
    assert type(default_project.id) == uuid.UUID


def test_getting_nonexistent_project_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_project("blupus_project")


def test_updating_project(fresh_sql_zen_store: BaseZenStore):
    """Tests updating a project."""
    default_project = fresh_sql_zen_store.get_project("default")
    assert default_project.name == "default"
    default_project.name = "aria"
    fresh_sql_zen_store.update_project("default", default_project)
    assert fresh_sql_zen_store.list_projects()[0].name == "aria"


def test_updating_nonexisting_project_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests updating a nonexistent project raises an error."""
    new_project = ProjectModel(name="arias_project")
    with pytest.raises(KeyError):
        fresh_sql_zen_store.update_project("blupus_project", new_project)


def test_deleting_project(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a project."""
    fresh_sql_zen_store.delete_project("default")
    assert len(fresh_sql_zen_store.list_projects()) == 0


def test_deleting_nonexistent_project_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests deleting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.delete_project("blupus_project")


#  .-----
# | TEAMS
# '------


def test_list_teams(fresh_sql_zen_store: BaseZenStore):
    """Tests listing teams."""
    assert len(fresh_sql_zen_store.teams) == 0


def test_create_team(fresh_sql_zen_store: BaseZenStore):
    """Tests creating a team."""
    assert len(fresh_sql_zen_store.teams) == 0
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    assert len(fresh_sql_zen_store.teams) == 1
    assert fresh_sql_zen_store.teams[0].name == "arias_team"


def test_get_team(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a team."""
    assert len(fresh_sql_zen_store.teams) == 0
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    assert fresh_sql_zen_store.get_team("arias_team").name == "arias_team"


def test_get_nonexistent_team_raises_error(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_team("blupus_team")


def test_delete_team_works(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a team."""
    assert len(fresh_sql_zen_store.teams) == 0
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    assert len(fresh_sql_zen_store.teams) == 1
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    fresh_sql_zen_store.delete_team(new_team_id)
    assert len(fresh_sql_zen_store.teams) == 0


def test_nonexistent_team_raises_error(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.delete_team(uuid.uuid4())


def test_adding_user_to_team(fresh_sql_zen_store: BaseZenStore):
    """Tests adding a user to a team."""
    assert len(fresh_sql_zen_store.teams) == 0
    team_name = "arias_team"
    new_team = TeamModel(name=team_name)
    fresh_sql_zen_store.create_team(new_team)
    current_user_id = fresh_sql_zen_store.active_user.id
    fresh_sql_zen_store.add_user_to_team(
        user_name_or_id="default", team_name_or_id=team_name
    )
    assert (
        fresh_sql_zen_store.get_users_for_team(team_name)[0].id
        == current_user_id
    )


def test_adding_nonexistent_user_to_nonexistent_team_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.add_user_to_team(uuid.uuid4(), uuid.uuid4())


def test_adding_nonexistent_user_to_real_team_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    with pytest.raises(KeyError):
        fresh_sql_zen_store.add_user_to_team(uuid.uuid4(), new_team_id)


def test_adding_real_user_to_nonexistent_team_raises_error(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests adding a nonexistent user to a team raises an error."""
    current_user_id = fresh_sql_zen_store.active_user.id
    with pytest.raises(KeyError):
        fresh_sql_zen_store.add_user_to_team(current_user_id, uuid.uuid4())


def test_removing_user_from_team_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests removing a user from a team."""
    assert len(fresh_sql_zen_store.teams) == 0
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    current_user_id = fresh_sql_zen_store.active_user.id
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    fresh_sql_zen_store.add_user_to_team(current_user_id, new_team_id)
    assert len(fresh_sql_zen_store.get_users_for_team(new_team_id)) == 1
    fresh_sql_zen_store.remove_user_from_team(current_user_id, new_team_id)
    assert len(fresh_sql_zen_store.get_users_for_team(new_team_id)) == 0


def test_removing_nonexistent_user_from_team_fails(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests removing a nonexistent user from a team raises an error."""
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    with pytest.raises(KeyError):
        fresh_sql_zen_store.remove_user_from_team(uuid.uuid4(), new_team_id)


def test_getting_user_from_nonexistent_team_fails(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting a user from a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_users_for_team(uuid.uuid4())


def test_getting_user_for_team(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a user from a team."""
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    current_user_id = fresh_sql_zen_store.active_user.id
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    fresh_sql_zen_store.add_user_to_team(current_user_id, new_team_id)
    users_for_team = fresh_sql_zen_store.get_users_for_team(new_team_id)
    assert len(users_for_team) == 1
    assert users_for_team[0].id == current_user_id


def test_getting_team_for_user(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a team for a user."""
    new_team = TeamModel(name="arias_team")
    fresh_sql_zen_store.create_team(new_team)
    current_user_id = fresh_sql_zen_store.active_user.id
    new_team_id = fresh_sql_zen_store.get_team("arias_team").id
    fresh_sql_zen_store.add_user_to_team(current_user_id, new_team_id)
    teams_for_user = fresh_sql_zen_store.get_teams_for_user(current_user_id)
    assert len(teams_for_user) == 1
    assert teams_for_user[0].id == new_team_id


#  .------.
# | USERS |
# '-------'


def test_active_user_property(fresh_sql_zen_store: BaseZenStore):
    """Tests the active user property."""
    active_user = fresh_sql_zen_store.active_user
    assert active_user is not None


def test_active_user_name_property(fresh_sql_zen_store: BaseZenStore):
    """Tests the active user name property."""
    active_user_name = fresh_sql_zen_store.active_user_name
    assert active_user_name is not None
    assert active_user_name == fresh_sql_zen_store.active_user.name
    assert active_user_name == "default"


def test_users_property(fresh_sql_zen_store: BaseZenStore):
    """Tests the users property."""
    assert len(fresh_sql_zen_store.users) == 1
    assert fresh_sql_zen_store.users[0].name == "default"
    assert fresh_sql_zen_store.users[0] == fresh_sql_zen_store.active_user


def test_creating_user_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests creating a user."""
    assert len(fresh_sql_zen_store.users) == 1
    new_user = UserModel(name="aria")
    fresh_sql_zen_store.create_user(new_user)
    assert len(fresh_sql_zen_store.users) == 2
    assert fresh_sql_zen_store.get_user("aria") is not None


def test_creating_user_with_existing_name_fails(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests creating a user with an existing name fails."""
    new_user = UserModel(name="aria")
    fresh_sql_zen_store.create_user(new_user)
    with pytest.raises(EntityExistsError):
        fresh_sql_zen_store.create_user(new_user)


def test_getting_nonexistent_user_fails(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a nonexistent user fails."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_user("aria")


def test_getting_user_by_name_and_id_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting a user by name and id."""
    new_user = UserModel(name="aria")
    fresh_sql_zen_store.create_user(new_user)
    users = fresh_sql_zen_store.users
    new_user_id = str(users[1].id)
    user_by_name = fresh_sql_zen_store.get_user("aria")
    user_by_id = fresh_sql_zen_store.get_user(new_user_id)
    assert user_by_id == user_by_name
    assert len(users) == 2


def test_updating_user_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests updating a user."""
    new_user_model = UserModel(name="aria")
    fresh_sql_zen_store.create_user(new_user_model)
    new_user = fresh_sql_zen_store.get_user("aria")
    new_user.name = "blupus"
    fresh_sql_zen_store.update_user(new_user.id, new_user)
    assert fresh_sql_zen_store.get_user("blupus") is not None
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_user("aria")


def test_updating_nonexistent_user_fails(fresh_sql_zen_store: BaseZenStore):
    """Tests updating a nonexistent user fails."""
    new_user = UserModel(name="demonic_aria")
    with pytest.raises(KeyError):
        fresh_sql_zen_store.update_user(uuid.uuid4(), new_user)


def test_deleting_user_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a user."""
    new_user = UserModel(name="aria")
    fresh_sql_zen_store.create_user(new_user)
    new_user_id = fresh_sql_zen_store.get_user("aria").id
    assert len(fresh_sql_zen_store.users) == 2
    fresh_sql_zen_store.delete_user(new_user_id)
    assert len(fresh_sql_zen_store.users) == 1


#  .------.
# | ROLES |
# '-------'


def test_roles_property_with_fresh_store(fresh_sql_zen_store: BaseZenStore):
    """Tests the roles property with a fresh ZenStore."""
    assert len(fresh_sql_zen_store.roles) == 0


def test_creating_role(fresh_sql_zen_store: BaseZenStore):
    """Tests creating a role."""
    assert len(fresh_sql_zen_store.roles) == 0
    new_role = RoleModel(name="admin")
    fresh_sql_zen_store.create_role(new_role)
    assert len(fresh_sql_zen_store.roles) == 1
    assert fresh_sql_zen_store.get_role("admin") is not None


def test_creating_existing_role_fails(fresh_sql_zen_store: BaseZenStore):
    """Tests creating an existing role fails."""
    new_role = RoleModel(name="admin")
    fresh_sql_zen_store.create_role(new_role)
    with pytest.raises(EntityExistsError):
        fresh_sql_zen_store.create_role(new_role)
    assert len(fresh_sql_zen_store.roles) == 1


def test_getting_role_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a role."""
    new_role = RoleModel(name="admin")
    fresh_sql_zen_store.create_role(new_role)
    assert fresh_sql_zen_store.get_role("admin") is not None


def test_getting_nonexistent_role_fails(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a nonexistent role fails."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_role("admin")


def test_deleting_role_succeeds(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a role."""
    new_role = RoleModel(name="admin")
    fresh_sql_zen_store.create_role(new_role)
    assert len(fresh_sql_zen_store.roles) == 1
    new_role_id = str(fresh_sql_zen_store.get_role("admin").id)
    fresh_sql_zen_store.delete_role(new_role_id)
    assert len(fresh_sql_zen_store.roles) == 0
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_role(new_role_id)


def test_deleting_nonexistent_role_fails(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a nonexistent role fails."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.delete_role(uuid.uuid4())


#  .------.
# | ROLES |
# '-------'


def test_assigning_role_to_user_succeeds(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = str(fresh_sql_store_with_team.active_user.id)
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = str(fresh_sql_store_with_team.get_role("aria_feeder").id)
    fresh_sql_store_with_team.assign_role(new_role_id, current_user_id)

    assert len(fresh_sql_store_with_team.roles) == 1
    assert len(fresh_sql_store_with_team.role_assignments) == 1


def test_assigning_role_to_team_succeeds(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a team."""
    team_id = str(fresh_sql_store_with_team.get_team("arias_team").id)
    new_role = RoleModel(name="blupus_friend")
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = fresh_sql_store_with_team.get_role("blupus_friend").id
    fresh_sql_store_with_team.assign_role(new_role_id, team_id, is_user=False)

    assert len(fresh_sql_store_with_team.roles) == 1
    assert len(fresh_sql_store_with_team.role_assignments) == 1
    assert (
        len(
            fresh_sql_store_with_team.list_role_assignments(
                user_name_or_id=fresh_sql_store_with_team.active_user.id
            )
        )
        == 1
    )


def test_assigning_role_if_assignment_already_exists(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests assigning a role to a user if the assignment already exists."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = str(fresh_sql_store_with_team.active_user.id)
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = str(fresh_sql_store_with_team.get_role("aria_feeder").id)
    fresh_sql_store_with_team.assign_role(new_role_id, current_user_id)
    with pytest.raises(EntityExistsError):
        fresh_sql_store_with_team.assign_role(new_role_id, current_user_id)

    assert len(fresh_sql_store_with_team.roles) == 1
    assert len(fresh_sql_store_with_team.role_assignments) == 1


def test_revoking_role_for_user_succeeds(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a user."""
    new_role = RoleModel(name="aria_feeder")
    current_user_id = str(fresh_sql_store_with_team.active_user.id)
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = str(fresh_sql_store_with_team.get_role("aria_feeder").id)
    fresh_sql_store_with_team.assign_role(new_role_id, current_user_id)
    fresh_sql_store_with_team.revoke_role(new_role_id, current_user_id)

    assert len(fresh_sql_store_with_team.roles) == 1
    assert len(fresh_sql_store_with_team.role_assignments) == 0


def test_revoking_role_for_team_succeeds(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a team."""
    team_id = str(fresh_sql_store_with_team.get_team("arias_team").id)
    new_role = RoleModel(name="blupus_friend")
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = str(fresh_sql_store_with_team.get_role("blupus_friend").id)
    fresh_sql_store_with_team.assign_role(new_role_id, team_id, is_user=False)
    fresh_sql_store_with_team.revoke_role(new_role_id, team_id, is_user=False)

    assert len(fresh_sql_store_with_team.roles) == 1
    assert len(fresh_sql_store_with_team.role_assignments) == 0


def test_revoking_nonexistent_role_fails(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests revoking a nonexistent role fails."""
    current_user_id = fresh_sql_store_with_team.active_user.id
    with pytest.raises(KeyError):
        fresh_sql_store_with_team.revoke_role(uuid.uuid4(), current_user_id)


def test_revoking_role_for_nonexistent_user_fails(
    fresh_sql_store_with_team: BaseZenStore,
):
    """Tests revoking a role for a nonexistent user fails."""
    new_role = RoleModel(name="aria_feeder")
    fresh_sql_store_with_team.create_role(new_role)
    new_role_id = str(fresh_sql_store_with_team.get_role("aria_feeder").id)
    current_user_id = str(fresh_sql_store_with_team.active_user.id)
    fresh_sql_store_with_team.assign_role(new_role_id, current_user_id)
    with pytest.raises(KeyError):
        fresh_sql_store_with_team.revoke_role(new_role_id, uuid.uuid4())


#  .----------------.
# | METADATA_CONFIG |
# '-----------------'


def test_get_metadata_config_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting metadata config."""
    metadata_config = fresh_sql_zen_store.get_metadata_config()
    assert metadata_config is not None


#  .-------.
# | STACKS |
# '--------'


def test_list_stacks_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests listing stacks."""
    current_project_id = str(fresh_sql_zen_store.list_projects()[0].id)
    assert len(fresh_sql_zen_store.list_stacks(current_project_id)) == 1


def test_list_stacks_fails_with_nonexistent_project(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests listing stacks fails with nonexistent project."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.list_stacks(uuid.uuid4())


def test_get_stack_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting stack."""
    current_stack_id = fresh_sql_zen_store.list_stacks(
        project_name_or_id="default"
    )[0].id
    stack = fresh_sql_zen_store.get_stack(current_stack_id)
    assert stack is not None


def test_get_stack_fails_with_nonexistent_stack_id(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests getting stack fails with nonexistent stack id."""
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_stack(uuid.uuid4())


def test_register_stack_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests registering stack."""
    new_stack = StackModel(name="arias_stack", components={})
    fresh_sql_zen_store.register_stack(
        user_name_or_id="default",
        project_name_or_id="default",
        stack=new_stack,
    )
    stacks = fresh_sql_zen_store.list_stacks("default")
    assert len(stacks) == 2
    assert fresh_sql_zen_store.get_stack(stacks[0].id) is not None


def test_register_stack_fails_when_stack_exists(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests registering stack fails when stack exists."""
    new_stack = StackModel(name="default", components={})
    with pytest.raises(StackExistsError):
        fresh_sql_zen_store.register_stack(
            user_name_or_id="default",
            project_name_or_id="default",
            stack=new_stack,
        )


def test_updating_stack_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests updating stack."""
    current_stack_id = fresh_sql_zen_store.list_stacks(
        project_name_or_id="default"
    )[0].id
    new_stack = StackModel(name="arias_stack", components={})
    fresh_sql_zen_store.update_stack(current_stack_id, new_stack)
    assert fresh_sql_zen_store.get_stack(current_stack_id) is not None
    assert fresh_sql_zen_store.get_stack(current_stack_id).name == "arias_stack"


def test_updating_nonexistent_stack_fails(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests updating nonexistent stack fails."""
    new_stack = StackModel(name="arias_stack", components={})
    non_existent_stack_id = uuid.uuid4()
    with pytest.raises(KeyError):
        fresh_sql_zen_store.update_stack(non_existent_stack_id, new_stack)
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_stack(non_existent_stack_id)
    assert (
        fresh_sql_zen_store.get_stack(
            fresh_sql_zen_store.list_stacks(project_name_or_id="default")[0].id
        ).name
        != "arias_stack"
    )


# TODO: continue on to cover register, update and delete stacks
# DELETE
def test_deleting_default_stack_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests deleting stack."""
    current_stack_id = fresh_sql_zen_store.list_stacks(
        project_name_or_id="default"
    )[0].id
    fresh_sql_zen_store.delete_stack(current_stack_id)
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_stack(current_stack_id)


def test_deleting_nonexistent_stack_fails(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests deleting nonexistent stack fails."""
    non_existent_stack_id = uuid.uuid4()
    with pytest.raises(KeyError):
        fresh_sql_zen_store.delete_stack(non_existent_stack_id)


def test_deleting_a_stack_succeeds(
    fresh_sql_zen_store: BaseZenStore,
):
    """Tests deleting stack."""
    new_stack = StackModel(name="arias_stack", components={})
    fresh_sql_zen_store.register_stack(
        user_name_or_id="default",
        project_name_or_id="default",
        stack=new_stack,
    )
    stacks = fresh_sql_zen_store.list_stacks(project_name_or_id="default")
    assert len(stacks) == 2
    new_stack = [stack for stack in stacks if stack.name == "arias_stack"][0]
    fresh_sql_zen_store.delete_stack(new_stack.id)
    with pytest.raises(KeyError):
        fresh_sql_zen_store.get_stack(new_stack.id)
