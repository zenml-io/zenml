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
from typing import Dict, Union

import pytest

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.config.schedule import Schedule
from zenml.enums import (
    ArtifactType,
    ExecutionStatus,
    PermissionType,
    StackComponentType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.models import (
    ArtifactRequestModel,
    ComponentRequestModel,
    ComponentUpdateModel,
    FlavorRequestModel,
    PipelineRequestModel,
    PipelineRunUpdateModel,
    PipelineUpdateModel,
    ProjectRequestModel,
    ProjectUpdateModel,
    RoleAssignmentRequestModel,
    RoleRequestModel,
    RoleUpdateModel,
    StackRequestModel,
    StackUpdateModel,
    StepRunUpdateModel,
    TeamRequestModel,
    TeamUpdateModel,
    UserRequestModel,
    UserUpdateModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.models.schedule_model import (
    ScheduleRequestModel,
    ScheduleUpdateModel,
)
from zenml.zen_stores.base_zen_store import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_GUEST_ROLE,
    DEFAULT_PROJECT_NAME,
    DEFAULT_USERNAME,
    BaseZenStore,
)

DEFAULT_NAME = "default"

#  .--------
# | PROJECTS
# '---------


def test_only_one_default_project_present(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests that only one default project can be created."""
    assert len(sql_store["store"].list_projects()) == 1


def test_project_creation_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests project creation."""
    assert len(sql_store["store"].list_projects()) == 1
    new_project = ProjectRequestModel(name="arias_project")
    sql_store["store"].create_project(new_project)
    projects_list = sql_store["store"].list_projects()
    assert len(projects_list) == 2
    assert "arias_project" in [p.name for p in projects_list]


def test_get_project_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a project."""
    assert sql_store["default_project"].name == DEFAULT_PROJECT_NAME
    with does_not_raise():
        sql_store["store"].get_project(DEFAULT_PROJECT_NAME)
        sql_store["store"].get_project(sql_store["default_project"].id)


def test_getting_nonexistent_project_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_project("blupus_project")


def test_updating_default_project_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests updating the default project."""
    default_project = sql_store["store"].get_project(DEFAULT_PROJECT_NAME)
    assert default_project.name == DEFAULT_PROJECT_NAME
    project_update = ProjectUpdateModel(
        name="aria_project",
        description="Aria has taken possession of this project.",
    )
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_project(
            project_id=default_project.id, project_update=project_update
        )


def test_updating_project_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests updating a project."""
    new_project = ProjectRequestModel(name="arias_project")
    new_project = sql_store["store"].create_project(new_project)

    new_name = "axls_project"
    project_update = ProjectUpdateModel(
        name=new_name, description="Axl has taken possession of this project."
    )

    with does_not_raise():
        sql_store["store"].update_project(
            project_id=new_project.id, project_update=project_update
        )
    with does_not_raise():
        sql_store["store"].get_project(project_name_or_id=new_name)


def test_updating_nonexisting_project_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating a nonexistent project raises an error."""
    project_update = ProjectUpdateModel(name="arias_project")
    with pytest.raises(KeyError):
        sql_store["store"].update_project(
            project_id=uuid.uuid4(), project_update=project_update
        )


def test_deleting_project_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a project."""
    new_project = ProjectRequestModel(name="axls_project")
    new_project = sql_store["store"].create_project(new_project)
    with does_not_raise():
        sql_store["store"].delete_project("axls_project")
    assert len(sql_store["store"].list_projects()) == 1


def test_deleting_default_project_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting the default project."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_project(DEFAULT_NAME)


def test_deleting_nonexistent_project_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests deleting a nonexistent project raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_project("blupus_project")


#  .-----
# | TEAMS
# '------


def test_list_teams(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests listing teams."""
    assert len(sql_store["store"].list_teams()) == 0
    new_team = TeamRequestModel(name="arias_team")
    with does_not_raise():
        new_team = sql_store["store"].create_team(new_team)
    assert len(sql_store["store"].list_teams()) == 1


def test_create_team(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests creating a team."""
    new_team = TeamRequestModel(name="arias_team")
    with does_not_raise():
        new_team = sql_store["store"].create_team(new_team)
    assert sql_store["store"].get_team(new_team.name)


def test_get_team(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a team."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    assert sql_store["store"].get_team("arias_team").name == "arias_team"


def test_get_nonexistent_team_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].get_team("blupus_team")


def test_delete_team_works(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a team."""
    team_name = "arias_team"
    new_team = TeamRequestModel(name=team_name)
    new_team = sql_store["store"].create_team(new_team)
    assert new_team.name == team_name
    with does_not_raise():
        sql_store["store"].delete_team(new_team.id)
    with pytest.raises(KeyError):
        sql_store["store"].get_team(new_team.id)


def test_nonexistent_team_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a nonexistent team raises an error."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_team(uuid.uuid4())


def test_adding_user_to_team(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests adding a user to a team."""
    team_name = "arias_team"
    new_team = TeamRequestModel(name=team_name)
    new_team = sql_store["store"].create_team(new_team)

    current_user_id = sql_store["active_user"].id
    team_update = TeamUpdateModel(users=[current_user_id])
    team_update = sql_store["store"].update_team(
        team_id=new_team.id, team_update=team_update
    )

    assert current_user_id in team_update.user_ids
    # Make sure the team name has not been inadvertently changed
    assert sql_store["store"].get_team(new_team.id).name == team_name


def test_adding_nonexistent_user_to_real_team_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests adding a nonexistent user to a team raises an error."""
    new_team = TeamRequestModel(name="arias_team")
    new_team = sql_store["store"].create_team(new_team)
    nonexistent_id = uuid.uuid4()
    team_update = TeamUpdateModel(users=[nonexistent_id])
    with pytest.raises(KeyError):
        sql_store["store"].update_team(
            team_id=new_team.id, team_update=team_update
        )


def test_update_nonexistent_team_raises_error(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests adding a nonexistent user to a team raises an error."""
    team_update = TeamUpdateModel(name="axls_team")
    with pytest.raises(KeyError):
        sql_store["store"].update_team(
            team_id=uuid.uuid4(), team_update=team_update
        )


def test_removing_user_from_team_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests removing a user from a team."""
    new_team = TeamRequestModel(name="arias_team")
    new_team = sql_store["store"].create_team(new_team)

    current_user_id = sql_store["active_user"].id

    team_update = TeamUpdateModel(users=[current_user_id])
    updated_team = sql_store["store"].update_team(
        team_id=new_team.id, team_update=team_update
    )
    assert current_user_id in updated_team.user_ids
    team_update = TeamUpdateModel(users=[])
    updated_team = sql_store["store"].update_team(
        team_id=new_team.id, team_update=team_update
    )
    assert current_user_id not in updated_team.user_ids


def test_access_user_in_team_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a user from a team."""
    current_user_id = sql_store["active_user"].id

    new_team = TeamRequestModel(name="arias_team")
    new_team = sql_store["store"].create_team(new_team)
    assert len(new_team.users) == 0

    team_update = TeamUpdateModel(users=[current_user_id])
    team_update = sql_store["store"].update_team(
        team_id=new_team.id, team_update=team_update
    )

    assert len(team_update.users) == 1
    assert current_user_id in team_update.user_ids


def test_getting_team_for_user(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a team for a user."""
    new_team = TeamRequestModel(name="arias_team")
    sql_store["store"].create_team(new_team)
    current_user_id = sql_store["active_user"].id
    new_team = sql_store["store"].get_team("arias_team")
    team_update = TeamUpdateModel(users=[current_user_id])
    updated_team = sql_store["store"].update_team(
        team_id=new_team.id, team_update=team_update
    )
    assert len(updated_team.users) == 1


#  .------.
# | USERS |
# '-------'


def test_active_user_property(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests the active user can be queried with .get_user()."""
    active_user = sql_store["store"].get_user()
    assert active_user is not None
    assert active_user == sql_store["active_user"]


def test_users_property(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests the users property."""
    assert len(sql_store["store"].list_users()) == 1
    assert sql_store["store"].list_users()[0].name == DEFAULT_NAME
    assert sql_store["active_user"].name == DEFAULT_NAME
    assert sql_store["store"].list_users()[0] == sql_store["store"].get_user()
    assert sql_store["store"].list_users()[0] == sql_store["active_user"]


def test_creating_user_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests creating a user."""
    assert len(sql_store["store"].list_users()) == 1
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    assert len(sql_store["store"].list_users()) == 2
    assert sql_store["store"].get_user("aria") is not None


def test_creating_user_with_existing_name_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests creating a user with an existing name fails."""
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    with pytest.raises(EntityExistsError):
        sql_store["store"].create_user(new_user)


def test_getting_nonexistent_user_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a nonexistent user fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_user("aria")


def test_getting_user_by_name_and_id_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting a user by name and id."""
    new_user = UserRequestModel(name="aria")
    new_user = sql_store["store"].create_user(new_user)
    new_user_id = str(new_user.id)
    user_by_name = sql_store["store"].get_user("aria")
    user_by_id = sql_store["store"].get_user(new_user_id)
    assert user_by_id == user_by_name
    assert len(sql_store["store"].list_users()) == 2


def test_updating_user_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests updating a user."""
    new_user_model = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user_model)
    new_user = sql_store["store"].get_user("aria")

    new_user_name = "blupus"
    user_update = UserUpdateModel(name=new_user_name)
    sql_store["store"].update_user(
        user_id=new_user.id, user_update=user_update
    )

    assert sql_store["store"].get_user(new_user_name) is not None
    with pytest.raises(KeyError):
        sql_store["store"].get_user("aria")


def test_updating_default_user_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests that updating the default user is prohibited."""
    default_user = sql_store["store"].get_user(DEFAULT_USERNAME)
    assert default_user
    user_update = UserUpdateModel()
    user_update.name = "axl"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_user(
            user_id=default_user.id, user_update=user_update
        )


def test_updating_nonexistent_user_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests updating a nonexistent user fails."""
    new_user = UserUpdateModel(name="demonic_aria")

    with pytest.raises(KeyError):
        sql_store["store"].update_user(
            user_id=uuid.uuid4(), user_update=new_user
        )


def test_deleting_user_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a user."""
    new_user = UserRequestModel(name="aria")
    sql_store["store"].create_user(new_user)
    new_user_id = sql_store["store"].get_user("aria").id
    assert len(sql_store["store"].list_users()) == 2
    sql_store["store"].delete_user(new_user_id)
    assert len(sql_store["store"].list_users()) == 1


def test_deleting_default_user_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests that deleting the default user is prohibited."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_user("default")


#  .------.
# | ROLES |
# '-------'


def test_roles_property_with_fresh_store(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests the roles property with a fresh ZenStore."""
    assert len(sql_store["store"].roles) == 2


def test_creating_role(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
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


def test_creating_role_with_empty_permissions_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests creating a role."""
    assert len(sql_store["store"].roles) == 2
    roles_before = len(sql_store["store"].roles)

    new_role = RoleRequestModel(name="cat", permissions=set())
    sql_store["store"].create_role(new_role)
    assert len(sql_store["store"].roles) == roles_before + 1
    assert sql_store["store"].get_role("admin") is not None


def test_creating_role_with_existing_name_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
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


def test_creating_existing_role_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
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


def test_getting_role_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
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


def test_getting_nonexistent_role_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests getting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].get_role("random_role_that_does_not_exist")


def test_deleting_role_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
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


def test_deleting_nonexistent_role_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_role(uuid.uuid4())


def test_deleting_builtin_role_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests deleting a built-in role fails."""
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_role("admin")

    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_role("guest")


def test_updating_builtin_role_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
):
    """Tests updating a built-in role fails."""
    role = sql_store["store"].get_role(DEFAULT_ADMIN_ROLE)
    role_update = RoleUpdateModel(name="cat_feeder")

    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_role(
            role_id=role.id, role_update=role_update
        )

    role = sql_store["store"].get_role(DEFAULT_GUEST_ROLE)
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_role(
            role_id=role.id, role_update=role_update
        )


#  .----------------
# | ROLE ASSIGNMENTS
# '-----------------


def test_assigning_role_to_user_succeeds(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests assigning a role to a user."""
    role_assignment = RoleAssignmentRequestModel(
        role=sql_store_with_user_team_role["role"].id,
        user=sql_store_with_user_team_role["user"].id,
        is_user=True,
        project=None,
    )
    with does_not_raise():
        (
            sql_store_with_user_team_role["store"].create_role_assignment(
                role_assignment
            )
        )


def test_assigning_role_to_team_succeeds(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests assigning a role to a team."""
    role_assignment = RoleAssignmentRequestModel(
        role=sql_store_with_user_team_role["role"].id,
        team=sql_store_with_user_team_role["team"].id,
        is_user=True,
        project=None,
    )
    with does_not_raise():
        (
            sql_store_with_user_team_role["store"].create_role_assignment(
                role_assignment
            )
        )


def test_assigning_role_if_assignment_already_exists_fails(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests assigning a role to a user if the assignment already exists."""
    role_assignment = RoleAssignmentRequestModel(
        role=sql_store_with_user_team_role["role"].id,
        user=sql_store_with_user_team_role["user"].id,
        is_user=True,
        project=None,
    )
    with does_not_raise():
        (
            sql_store_with_user_team_role["store"].create_role_assignment(
                role_assignment
            )
        )
    with pytest.raises(EntityExistsError):
        (
            sql_store_with_user_team_role["store"].create_role_assignment(
                role_assignment
            )
        )


def test_revoking_role_for_user_succeeds(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests revoking a role for a user."""
    role_assignment = RoleAssignmentRequestModel(
        role=sql_store_with_user_team_role["role"].id,
        user=sql_store_with_user_team_role["user"].id,
        is_user=True,
        project=None,
    )
    with does_not_raise():
        role_assignment = sql_store_with_user_team_role[
            "store"
        ].create_role_assignment(role_assignment)
        sql_store_with_user_team_role["store"].delete_role_assignment(
            role_assignment_id=role_assignment.id
        )
    with pytest.raises(KeyError):
        sql_store_with_user_team_role["store"].get_role_assignment(
            role_assignment_id=role_assignment.id
        )


def test_revoking_role_for_team_succeeds(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests revoking a role for a team."""
    role_assignment = RoleAssignmentRequestModel(
        role=sql_store_with_user_team_role["role"].id,
        team=sql_store_with_user_team_role["team"].id,
        is_user=True,
        project=None,
    )
    with does_not_raise():
        role_assignment = sql_store_with_user_team_role[
            "store"
        ].create_role_assignment(role_assignment)
        sql_store_with_user_team_role["store"].delete_role_assignment(
            role_assignment_id=role_assignment.id
        )
    with pytest.raises(KeyError):
        sql_store_with_user_team_role["store"].get_role_assignment(
            role_assignment_id=role_assignment.id
        )


def test_revoking_nonexistent_role_fails(
    sql_store_with_user_team_role: Dict[
        str, Union[BaseZenStore, BaseResponseModel]
    ],
):
    """Tests revoking a nonexistent role fails."""
    with pytest.raises(KeyError):
        sql_store_with_user_team_role["store"].delete_role_assignment(
            role_assignment_id=uuid.uuid4()
        )


#  .-------.
# | STACKS |
# '--------'


def test_list_stacks_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing stacks."""
    assert len(sql_store["store"].list_stacks()) == 1


def test_list_stacks_fails_with_nonexistent_project(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing stacks fails with nonexistent project."""
    with pytest.raises(KeyError):
        sql_store["store"].list_stacks(project_name_or_id=uuid.uuid4())


def test_get_stack_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting stack."""
    current_stack_id = sql_store["store"].list_stacks()[0].id
    stack = sql_store["store"].get_stack(stack_id=current_stack_id)
    assert stack is not None


def test_get_stack_fails_with_nonexistent_stack_id(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting stack fails with nonexistent stack id."""
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(uuid.uuid4())


def test_register_stack_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating stack."""
    new_stack = StackRequestModel(
        name="arias_stack",
        description="Aria likes her stacks.",
        components={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    new_stack = sql_store["store"].create_stack(
        stack=new_stack,
    )
    new_stack_name = "axls_stack"
    stack_update = StackUpdateModel(name=new_stack_name)
    sql_store["store"].update_stack(
        stack_id=new_stack.id, stack_update=stack_update
    )
    assert sql_store["store"].get_stack(new_stack.id) is not None
    assert sql_store["store"].get_stack(new_stack.id).name == new_stack_name
    # Ensure unset fields of the `UpdateModel` are not changed
    assert (
        sql_store["store"].get_stack(new_stack.id).description
        == new_stack.description
    )


def test_updating_default_stack_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests that updating the default stack is prohibited."""
    default_stack_id = sql_store["default_stack"].id
    default_stack = sql_store["store"].get_stack(default_stack_id)
    new_stack_name = "axls_stack"
    stack_update = StackUpdateModel(name=new_stack_name)
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack(
            stack_id=default_stack.id, stack_update=stack_update
        )


def test_updating_nonexistent_stack_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating nonexistent stack fails."""
    current_stack_id = sql_store["default_stack"].id
    new_stack_name = "axls_stack"
    stack_update = StackUpdateModel(name=new_stack_name)
    nonexistent_id = uuid.uuid4()
    with pytest.raises(KeyError):
        sql_store["store"].update_stack(
            stack_id=nonexistent_id, stack_update=stack_update
        )
    with pytest.raises(KeyError):
        sql_store["store"].get_stack(nonexistent_id)
    assert sql_store["store"].get_stack(current_stack_id).name != "arias_stack"


def test_deleting_stack_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests that deleting the default stack is prohibited."""
    default_stack_id = sql_store["default_stack"].id
    with pytest.raises(IllegalOperationError):
        sql_store["store"].delete_stack(default_stack_id)


def test_deleting_nonexistent_stack_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests deleting nonexistent stack fails."""
    non_existent_stack_id = uuid.uuid4()
    with pytest.raises(KeyError):
        sql_store["store"].delete_stack(non_existent_stack_id)


def test_deleting_a_stack_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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


# ---------
# Pipelines
# ---------


def test_create_pipeline_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests creating pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests creating identical pipeline fails."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    sql_store["store"].create_pipeline(pipeline=new_pipeline)
    pipeline_id = sql_store["store"].list_pipelines()[0].id
    pipeline = sql_store["store"].get_pipeline(pipeline_id=pipeline_id)
    assert pipeline is not None
    assert pipeline.name == "arias_pipeline"


def test_get_pipeline_fails_for_nonexistent_pipeline(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting pipeline fails for nonexistent pipeline."""
    with pytest.raises(KeyError):
        sql_store["store"].get_pipeline(uuid.uuid4())


def test_list_pipelines_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing pipelines."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
        name="arias_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    new_pipeline = sql_store["store"].create_pipeline(pipeline=new_pipeline)

    pipeline_update = PipelineUpdateModel(
        name="blupus_ka_pipeline",
    )
    with does_not_raise():
        pipeline_update = sql_store["store"].update_pipeline(
            pipeline_id=new_pipeline.id, pipeline_update=pipeline_update
        )
    assert pipeline_update is not None
    assert pipeline_update.name == "blupus_ka_pipeline"
    assert pipeline_update.spec == new_pipeline.spec


def test_updating_nonexistent_pipeline_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating nonexistent pipeline fails."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    pipeline_update = PipelineUpdateModel(
        name="blupus_ka_pipeline",
        project=project_id,
        user=user_id,
        spec=spec,
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_pipeline(
            pipeline_id=uuid.uuid4(), pipeline_update=pipeline_update
        )


def test_deleting_pipeline_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests deleting pipeline."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    spec = PipelineSpec(steps=[])
    new_pipeline = PipelineRequestModel(
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests deleting nonexistent pipeline fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_pipeline(uuid.uuid4())


# ---------
# Schedules
# ---------


def test_create_schedule_succeeds(sql_store):
    """Tests creating schedule."""
    project_id = sql_store["default_project"].id
    user_id = sql_store["active_user"].id
    orchestrator_id = (
        sql_store["default_stack"].components["orchestrator"][0].id
    )
    schedule = Schedule(cron_expression="*/5 * * * *")
    schedule = ScheduleRequestModel(
        name="arias_schedule",
        project=project_id,
        user=user_id,
        pipeline_id=None,
        orchestrator_id=orchestrator_id,
        active=True,
        cron_expression=schedule.cron_expression,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        interval_second=schedule.interval_second,
        catchup=schedule.catchup,
    )
    schedules = sql_store["store"].list_schedules()
    assert len(schedules) == 0
    with does_not_raise():
        schedule = sql_store["store"].create_schedule(schedule=schedule)
    assert schedule is not None
    assert schedule.name == "arias_schedule"
    schedules = sql_store["store"].list_schedules()
    assert len(schedules) == 1


def test_getting_schedule_succeeds(sql_store_with_scheduled_run):
    """Tests getting schedule."""
    schedule_id = sql_store_with_scheduled_run["schedule"].id
    with does_not_raise():
        schedule = sql_store_with_scheduled_run["store"].get_schedule(
            schedule_id
        )
        assert schedule is not None
        assert schedule.name == sql_store_with_scheduled_run["schedule"].name


def test_getting_nonexistent_schedule_fails(sql_store_with_scheduled_run):
    """Tests getting nonexistent schedule fails."""
    with pytest.raises(KeyError):
        sql_store_with_scheduled_run["store"].get_schedule(uuid.uuid4())


def test_list_schedules_succeeds(sql_store_with_scheduled_run):
    """Tests listing schedules."""
    schedules = sql_store_with_scheduled_run["store"].list_schedules()
    assert len(schedules) == 1


def test_updating_schedule_succeeds(sql_store_with_scheduled_run):
    """Tests updating schedule."""
    schedule_id = sql_store_with_scheduled_run["schedule"].id
    schedule_update = ScheduleUpdateModel(
        name="blupus_schedule",
        active=False,
    )
    with does_not_raise():
        updated_schedule = sql_store_with_scheduled_run[
            "store"
        ].update_schedule(
            schedule_id=schedule_id, schedule_update=schedule_update
        )
    assert updated_schedule is not None
    assert updated_schedule.name == "blupus_schedule"
    assert updated_schedule.active is False
    assert (
        updated_schedule.created
        == sql_store_with_scheduled_run["schedule"].created
    )
    assert (
        updated_schedule.updated
        != sql_store_with_scheduled_run["schedule"].updated
    )


def test_updating_nonexistent_schedule_fails(sql_store_with_scheduled_run):
    """Tests updating nonexistent schedule fails."""
    schedule_update = ScheduleUpdateModel(
        name="blupus_schedule",
        active=False,
    )
    with pytest.raises(KeyError):
        sql_store_with_scheduled_run["store"].update_schedule(
            schedule_id=uuid.uuid4(), schedule_update=schedule_update
        )


def test_deleting_schedule_succeeds(sql_store_with_scheduled_run):
    """Tests deleting schedule."""
    schedule_id = sql_store_with_scheduled_run["schedule"].id
    schedules = sql_store_with_scheduled_run["store"].list_schedules()
    assert len(schedules) == 1
    sql_store_with_scheduled_run["store"].delete_schedule(schedule_id)
    schedules = sql_store_with_scheduled_run["store"].list_schedules()
    assert len(schedules) == 0
    with pytest.raises(KeyError):
        sql_store_with_scheduled_run["store"].get_schedule(schedule_id)


def test_deleting_nonexistent_schedule_fails(sql_store_with_scheduled_run):
    """Tests deleting nonexistent schedule fails."""
    with pytest.raises(KeyError):
        sql_store_with_scheduled_run["store"].delete_schedule(uuid.uuid4())


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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing runs returns nothing when no runs exist."""
    runs = sql_store["store"].list_runs()
    assert len(runs) == 0

    with pytest.raises(KeyError):
        sql_store["store"].list_runs(project_name_or_id=uuid.uuid4())

    false_stack_runs = sql_store["store"].list_runs(stack_id=uuid.uuid4())
    assert len(false_stack_runs) == 0

    false_run_name_runs = sql_store["store"].list_runs(name="not_arias_run")
    assert len(false_run_name_runs) == 0

    with pytest.raises(KeyError):
        sql_store["store"].list_runs(user_name_or_id=uuid.uuid4())

    false_pipeline_runs = sql_store["store"].list_runs(
        pipeline_id=uuid.uuid4()
    )
    assert len(false_pipeline_runs) == 0


def test_list_runs_is_ordered(sql_store_with_runs):
    """Tests listing runs returns ordered runs."""
    runs = sql_store_with_runs["store"].list_runs()
    assert len(runs) == 10
    assert all(
        runs[i].created <= runs[i + 1].created for i in range(len(runs) - 1)
    )


def test_update_run_succeeds(sql_store_with_run):
    """Tests updating run."""
    run_id = sql_store_with_run["pipeline_run"].id
    run = sql_store_with_run["store"].get_run(run_id)
    assert run.status == ExecutionStatus.COMPLETED
    run_update = PipelineRunUpdateModel(
        status=ExecutionStatus.FAILED,
    )
    sql_store_with_run["store"].update_run(run_id, run_update)
    run = sql_store_with_run["store"].get_run(run_id)
    assert run.status == ExecutionStatus.FAILED


def test_update_nonexistent_run_fails(sql_store):
    """Tests updating nonexistent run fails."""
    with pytest.raises(KeyError):
        sql_store["store"].update_run(uuid.uuid4(), PipelineRunUpdateModel())


def test_deleting_run_succeeds(sql_store_with_run):
    """Tests deleting run."""
    assert len(sql_store_with_run["store"].list_runs()) == 1
    run_id = sql_store_with_run["pipeline_run"].id
    sql_store_with_run["store"].delete_run(run_id)
    assert len(sql_store_with_run["store"].list_runs()) == 0
    with pytest.raises(KeyError):
        sql_store_with_run["store"].get_run(run_id)


def test_deleting_nonexistent_run_fails(sql_store):
    """Tests deleting nonexistent run fails."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_run(uuid.uuid4())


def test_deleting_run_deletes_steps(sql_store_with_run):
    """Tests deleting run deletes its steps."""
    assert len(sql_store_with_run["store"].list_run_steps()) == 2
    run_id = sql_store_with_run["pipeline_run"].id
    sql_store_with_run["store"].delete_run(run_id)
    assert len(sql_store_with_run["store"].list_run_steps()) == 0


# ------------------
# Pipeline run steps
# ------------------


def test_get_run_step_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step."""
    pipeline_step = sql_store_with_run["step"]
    run_step = sql_store_with_run["store"].get_run_step(
        step_run_id=pipeline_step.id
    )
    assert run_step is not None
    assert run_step.id == pipeline_step.id
    assert run_step == pipeline_step


def test_get_run_step_fails_when_step_does_not_exist(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting run step fails when step does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_run_step(step_run_id=uuid.uuid4())


def test_get_run_step_outputs_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step outputs."""
    pipeline_step = sql_store_with_run["step"]
    store = sql_store_with_run["store"]
    run_step_outputs = store.get_run_step(pipeline_step.id).output_artifacts
    assert len(run_step_outputs) == 1


def test_get_run_step_inputs_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step inputs."""
    pipeline_step = sql_store_with_run["step"]
    store = sql_store_with_run["store"]
    run_step_inputs = store.get_run_step(pipeline_step.id).input_artifacts
    assert len(run_step_inputs) == 1


def test_get_run_step_status_succeeds(
    sql_store_with_run: BaseZenStore,
):
    """Tests getting run step status."""
    pipeline_step = sql_store_with_run["step"]
    run_step_status = (
        sql_store_with_run["store"]
        .get_run_step(step_run_id=pipeline_step.id)
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


def test_update_run_step_succeeds(sql_store_with_run):
    """Tests updating run step."""
    step_run = sql_store_with_run["step"]
    store = sql_store_with_run["store"]
    step_run = store.get_run_step(step_run_id=step_run.id)
    assert step_run.status == ExecutionStatus.COMPLETED
    run_update = StepRunUpdateModel(status=ExecutionStatus.FAILED)
    updated_run = store.update_run_step(step_run.id, run_update)
    assert updated_run.status == ExecutionStatus.FAILED
    step_run = store.get_run_step(step_run_id=step_run.id)
    assert step_run.status == ExecutionStatus.FAILED


def test_update_run_step_fails_when_step_does_not_exist(sql_store):
    """Tests updating run step fails when step does not exist."""
    run_update = StepRunUpdateModel(status=ExecutionStatus.FAILED)
    with pytest.raises(KeyError):
        sql_store["store"].update_run_step(uuid.uuid4(), run_update)


# ---------
# Artifacts
# ---------


def test_create_artifact_succeeds(sql_store):
    """Tests creating artifact."""
    artifact_name = "test_artifact"
    artifact = ArtifactRequestModel(
        name=artifact_name,
        type=ArtifactType.DATA,
        uri="",
        materializer="",
        data_type="",
        user=sql_store["active_user"].id,
        project=sql_store["default_project"].id,
    )
    with does_not_raise():
        created_artifact = sql_store["store"].create_artifact(
            artifact=artifact
        )
        assert created_artifact.name == artifact_name


def get_artifact_succeeds(sql_store_with_run):
    """Tests getting artifact."""
    artifact = sql_store_with_run["store"].get_artifact(
        artifact_id=sql_store_with_run["artifact"].id
    )
    assert artifact is not None
    assert artifact == sql_store_with_run["artifact"]


def test_get_artifact_fails_when_artifact_does_not_exist(sql_store):
    """Tests getting artifact fails when artifact does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_artifact(artifact_id=uuid.uuid4())


def test_list_artifacts_succeeds(sql_store_with_run):
    """Tests listing artifacts."""
    artifacts = sql_store_with_run["store"].list_artifacts()
    assert len(artifacts) == 2
    assert artifacts[0] == sql_store_with_run["artifact"]


def test_list_unused_artifacts(sql_store_with_run):
    """Tests listing with `unused=True` only returns unused artifacts."""
    artifacts = sql_store_with_run["store"].list_artifacts()
    assert len(artifacts) == 2
    artifacts = sql_store_with_run["store"].list_artifacts(only_unused=True)
    assert len(artifacts) == 0
    run_id = sql_store_with_run["pipeline_run"].id
    sql_store_with_run["store"].delete_run(run_id)
    artifacts = sql_store_with_run["store"].list_artifacts(only_unused=True)
    assert len(artifacts) == 2


def test_delete_artifact_succeeds(sql_store_with_run):
    """Tests deleting artifact."""
    artifact_id = sql_store_with_run["artifact"].id
    assert len(sql_store_with_run["store"].list_artifacts()) == 2
    sql_store_with_run["store"].delete_artifact(artifact_id=artifact_id)
    assert len(sql_store_with_run["store"].list_artifacts()) == 1
    with pytest.raises(KeyError):
        sql_store_with_run["store"].get_artifact(artifact_id=artifact_id)


def test_delete_artifact_fails_when_artifact_does_not_exist(sql_store):
    """Tests deleting artifact fails when artifact does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_artifact(artifact_id=uuid.uuid4())


# ----------------
# Stack components
# ----------------


def test_create_stack_component_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting stack component."""
    components = sql_store["default_stack"].components
    component_id = list(components.values())[0][0].id
    with does_not_raise():
        sql_store["store"].get_stack_component(component_id=component_id)


def test_get_stack_component_fails_when_component_does_not_exist(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting stack component fails when component does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_stack_component(component_id=uuid.uuid4())


def test_list_stack_components_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing stack components fails when project does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].list_stack_components(
            project_name_or_id=uuid.uuid4()
        )


def test_list_stack_components_works_with_filters(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    component_update = ComponentUpdateModel(name=updated_orchestrator_name)
    with does_not_raise():
        updated_component = sql_store["store"].update_stack_component(
            component_id=orchestrator.id, component_update=component_update
        )
        assert updated_component.name == updated_orchestrator_name


def test_update_default_stack_component_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]]
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

    component_update = ComponentUpdateModel(name="aria")
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack_component(
            component_id=default_orchestrator.id,
            component_update=component_update,
        )

    default_orchestrator.name = "axl"
    with pytest.raises(IllegalOperationError):
        sql_store["store"].update_stack_component(
            component_id=default_artifact_store.id,
            component_update=component_update,
        )


def test_update_stack_component_fails_when_component_does_not_exist(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests updating stack component fails when component does not exist."""
    stack_component = ComponentUpdateModel(
        name="nonexistent",
        type=StackComponentType.ORCHESTRATOR,
        flavor="default",
        configuration={},
        project=sql_store["default_project"].id,
        user=sql_store["active_user"].id,
    )
    with pytest.raises(KeyError):
        sql_store["store"].update_stack_component(
            component_id=uuid.uuid4(), component_update=stack_component
        )


def test_delete_stack_component_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    orchestrators = sql_store["store"].list_stack_components(
        project_name_or_id=sql_store["default_project"].name,
        type=StackComponentType.ORCHESTRATOR,
    )
    assert len(orchestrators) == 2
    with does_not_raise():
        sql_store["store"].delete_stack_component(
            component_id=created_component.id
        )
        orchestrators = sql_store["store"].list_stack_components(
            project_name_or_id=sql_store["default_project"].name,
            type=StackComponentType.ORCHESTRATOR,
        )
    assert len(orchestrators) == 1
    with pytest.raises(KeyError):
        sql_store["store"].get_stack_component(
            component_id=created_component.id
        )


def test_delete_default_stack_component_fails(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests deleting stack component fails when component does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].delete_stack_component(component_id=uuid.uuid4())


# -----------------------
# Stack component flavors
# -----------------------


def test_create_stack_component_flavor_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
        new_flavor = sql_store["store"].create_flavor(flavor=verata_flavor)

        assert (
            sql_store["store"].get_flavor(flavor_id=new_flavor.id).name
            == flavor_name
        )


def test_get_flavor_fails_when_flavor_does_not_exist(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests getting stack component flavor fails when flavor does not exist."""
    with pytest.raises(KeyError):
        sql_store["store"].get_flavor(flavor_id=uuid.uuid4())


def test_list_flavors_succeeds(
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
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
    sql_store: Dict[str, Union[BaseZenStore, BaseResponseModel]],
):
    """Tests listing stack component flavors fails with nonexistent project."""
    with pytest.raises(KeyError):
        sql_store["store"].list_flavors(
            project_name_or_id="nonexistent",
            component_type=StackComponentType.ORCHESTRATOR,
        )
