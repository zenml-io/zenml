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
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    ENV_ZENML_PROFILE_NAME,
    IS_EMPTY,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS, USERS, TEAMS, PROJECTS, ROLES, ROLE_ASSIGNMENTS
)
from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentExistsError, StackExistsError, EntityExistsError
from zenml.repository import Repository
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import StackComponentWrapper, StackWrapper, User, Team, Project, Role, RoleAssignment


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError


profile_configuration_json = os.environ.get("ZENML_PROFILE_CONFIGURATION")
profile_name = os.environ.get(ENV_ZENML_PROFILE_NAME)

# Hopefully profile configuration was passed as env variable:
if profile_configuration_json:
    profile = ProfileConfiguration.parse_raw(profile_configuration_json)
# Otherwise check if profile name was passed as env variable:
elif profile_name:
    profile = (
        GlobalConfiguration().get_profile(profile_name)
        or Repository().active_profile
    )
# Fallback to what Repository thinks is the active profile
else:
    profile = Repository().active_profile


if profile.store_type == StoreType.REST:
    raise ValueError(
        "Service cannot be started with REST store type. Make sure you "
        "specify a profile with a non-networked persistence backend "
        "when trying to start the Zen Service. (use command line flag "
        "`--profile=$PROFILE_NAME` or set the env variable "
        f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
        "other than the currently active one)"
    )
zen_store: BaseZenStore = Repository.create_store(
    profile, skip_default_stack=True
)

app = FastAPI(title="ZenML", version=zenml.__version__)

# to run this file locally, execute:
# uvicorn zenml.zen_service.zen_service_api:app --reload


class ErrorModel(BaseModel):
    detail: Any


error_response = dict(model=ErrorModel)


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation."""
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response."""
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response."""
    return HTTPException(status_code=409, detail=error_detail(error))


@app.get("/", response_model=ProfileConfiguration)
async def service_info() -> ProfileConfiguration:
    return profile


@app.head("/health")
@app.get("/health")
async def health() -> str:
    return "OK"


@app.get(IS_EMPTY, response_model=bool)
async def is_empty() -> bool:
    return zen_store.is_empty


@app.get(
    STACK_CONFIGURATIONS + "/{name}",
    response_model=Dict[StackComponentType, str],
    responses={404: error_response},
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    try:
        return zen_store.get_stack_configuration(name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(
    STACK_CONFIGURATIONS,
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    return zen_store.stack_configurations


@app.post(STACK_COMPONENTS, responses={409: error_response})
async def register_stack_component(
    component: StackComponentWrapper,
) -> None:
    try:
        zen_store.register_stack_component(component)
    except StackComponentExistsError as error:
        raise conflict(error) from error


@app.delete(STACKS + "/{name}", responses={404: error_response})
async def deregister_stack(name: str) -> None:
    try:
        zen_store.deregister_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(STACKS, response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    return zen_store.stacks


@app.get(
    STACKS + "/{name}",
    response_model=StackWrapper,
    responses={404: error_response},
)
async def get_stack(name: str) -> StackWrapper:
    try:
        return zen_store.get_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@app.post(
    STACKS,
    response_model=Dict[str, str],
    responses={409: error_response},
)
async def register_stack(stack: StackWrapper) -> Dict[str, str]:
    try:
        return zen_store.register_stack(stack)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error


@app.get(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=StackComponentWrapper,
    responses={404: error_response},
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> StackComponentWrapper:
    try:
        return zen_store.get_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(
    STACK_COMPONENTS + "/{component_type}",
    response_model=List[StackComponentWrapper],
)
async def get_stack_components(
    component_type: StackComponentType,
) -> List[StackComponentWrapper]:
    return zen_store.get_stack_components(component_type)


@app.delete(
    STACK_COMPONENTS + "/{component_type}/{name}",
    responses={404: error_response, 409: error_response},
)
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    try:
        return zen_store.deregister_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise conflict(error) from error


@app.get(USERS, response_model=List[User])
async def users() -> List[User]:
    return zen_store.users


@app.post(
    USERS,
    response_model=User,
    responses={409: error_response},
)
async def create_user(user: User) -> User:
    try:
        return zen_store.create_user(user.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@app.delete(USERS + "/{name}", responses={404: error_response})
async def delete_user(name: str) -> None:
    try:
        zen_store.delete_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(USERS + "/{name}/teams", response_model=List[Team], responses={404: error_response})
async def teams_for_user(name: str) -> List[Team]:
    try:
        return zen_store.get_teams_for_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(USERS + "/{name}/role_assignments", response_model=List[RoleAssignment], responses={404: error_response})
async def role_assignments_for_user(name: str, project_name: Optional[str] = None) -> List[RoleAssignment]:
    try:
        return zen_store.get_role_assignments_for_user(user_name=name, project_name=project_name, include_team_roles=False)
    except KeyError as error:
        raise not_found(error) from error


@app.get(TEAMS, response_model=List[Team])
async def teams() -> List[Team]:
    return zen_store.teams


@app.post(
    TEAMS,
    response_model=Team,
    responses={409: error_response},
)
async def create_team(team: Team) -> Team:
    try:
        return zen_store.create_team(team.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@app.delete(TEAMS + "/{name}", responses={404: error_response})
async def delete_team(name: str) -> None:
    try:
        zen_store.delete_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error

@app.get(TEAMS + "/{name}/users", response_model=List[User], responses={404: error_response})
async def users_for_team(name: str) -> List[User]:
    try:
        return zen_store.get_users_for_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error

@app.post(TEAMS + "/{name}/users", responses={404: error_response})
async def add_user_to_team(name: str, user: User) -> None:
    try:
        zen_store.add_user_to_team(team_name=name, user_name=user.name)
    except KeyError as error:
        raise not_found(error) from error

@app.delete(TEAMS + "/{team_name}/users/{user_name}", responses={404: error_response})
async def remove_user_from_team(team_name: str, user_name: str) -> None:
    try:
        zen_store.remove_user_from_team(team_name=team_name, user_name=user_name)
    except KeyError as error:
        raise not_found(error) from error

@app.get(TEAMS + "/{name}/role_assignments", response_model=List[RoleAssignment], responses={404: error_response})
async def role_assignments_for_team(name: str, project_name: Optional[str] = None) -> List[RoleAssignment]:
    try:
        return zen_store.get_role_assignments_for_team(team_name=name, project_name=project_name)
    except KeyError as error:
        raise not_found(error) from error

@app.get(PROJECTS, response_model=List[Project])
async def projects() -> List[Project]:
    return zen_store.projects


@app.post(
    PROJECTS,
    response_model=Project,
    responses={409: error_response},
)
async def create_project(project: Project) -> Project:
    try:
        return zen_store.create_project(project_name=project.name, description=project.description)
    except EntityExistsError as error:
        raise conflict(error) from error


@app.delete(PROJECTS + "/{name}", responses={404: error_response})
async def delete_project(name: str) -> None:
    try:
        zen_store.delete_project(project_name=name)
    except KeyError as error:
        raise not_found(error) from error

@app.get(ROLES, response_model=List[Role])
async def roles() -> List[Role]:
    return zen_store.roles


@app.post(
    ROLES,
    response_model=Role,
    responses={409: error_response},
)
async def create_role(role: Role) -> Role:
    try:
        return zen_store.create_role(role.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@app.delete(ROLES + "/{name}", responses={404: error_response})
async def delete_role(name: str) -> None:
    try:
        zen_store.delete_role(role_name=name)
    except KeyError as error:
        raise not_found(error) from error

@app.get(ROLE_ASSIGNMENTS, response_model=List[RoleAssignment])
async def role_assignments() -> List[RoleAssignment]:
    return zen_store.role_assignments


@app.post(
    ROLE_ASSIGNMENTS,
    responses={404: error_response},
)
async def assign_role(data: Dict[str, Any]) -> None:
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.assign_role(role_name=role_name, entity_name=entity_name, project_name=project_name, is_user=is_user)
    except KeyError as error:
        raise not_found(error) from error


@app.delete(ROLE_ASSIGNMENTS, responses={404: error_response})
async def revoke_role(data: Dict[str, Any]) -> None:
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.revoke_role(role_name=role_name,
                                     entity_name=entity_name,
                                     project_name=project_name, is_user=is_user)
    except KeyError as error:
        raise not_found(error) from error
