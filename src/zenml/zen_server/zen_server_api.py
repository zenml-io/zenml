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
"""Zen Server API."""

import os
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_PROFILE_NAME, FLAVORS, TEAMS, USERS
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import EntityExistsError
from zenml.repository import Repository
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import FlavorWrapper, RoleAssignment, Team, User

from .routers import (
    auth_endpoints,
    metadata_config_endpoints,
    pipelines_endpoints,
    projects_endpoints,
    repositories_endpoints,
    roles_endpoints,
    runs_endpoints,
    stack_components_endpoints,
    stacks_endpoints,
    steps_endpoints,
    users_endpoints,
)

profile_name = os.environ.get(ENV_ZENML_PROFILE_NAME)

# Check if profile name was passed as env variable:
if profile_name:
    profile = (
        GlobalConfiguration().get_profile(profile_name)
        or Repository().active_profile
    )
# Fallback to what Repository thinks is the active profile
else:
    profile = Repository().active_profile

if profile.store_type == StoreType.REST:
    raise ValueError(
        "Server cannot be started with REST store type. Make sure you "
        "specify a profile with a non-networked persistence backend "
        "when trying to start the ZenServer. (use command line flag "
        "`--profile=$PROFILE_NAME` or set the env variable "
        f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
        "other than the currently active one)"
    )
# We initialize with track_analytics=False because we do not
# want to track anything server side.
zen_store: BaseZenStore = Repository.create_store(
    profile,
    skip_default_registrations=True,
    track_analytics=False,
    skip_migration=True,
)


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Any


error_response = dict(model=ErrorModel)

security = HTTPBasic()


def authorize(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Authorizes any request to the ZenServer.

    Right now this method only checks if the username provided as part of http
    basic auth credentials is registered in the ZenStore.

    Args:
        credentials: HTTP basic auth credentials passed to the request.

    Raises:
        HTTPException: If the username is not registered in the ZenStore.
    """
    try:
        zen_store.get_user(credentials.username)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username.",
        )


app = FastAPI(title="ZenML", version=zenml.__version__)
app.include_router(auth_endpoints.router)
app.include_router(metadata_config_endpoints.router)
app.include_router(pipelines_endpoints.router)
app.include_router(projects_endpoints.router)
app.include_router(repositories_endpoints.router)
app.include_router(roles_endpoints.router)
app.include_router(runs_endpoints.router)
app.include_router(stacks_endpoints.router)
app.include_router(stack_components_endpoints.router)
app.include_router(steps_endpoints.router)
# app.include_router(triggers_endpoints.router)
app.include_router(users_endpoints.router)


# Basic Health Endpoint


@app.head("/health")
@app.get("/health")
async def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


# TODO: Remove this after the rest of the routers are imported
# authed = APIRouter(
#     dependencies=[Depends(authorize)], responses={401: error_response}
# )

# to run this file locally, execute:
# uvicorn zenml.zen_server.zen_server_api:app --reload


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.

    Returns:
        List of strings representing the error.
    """
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 404.
    """
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 409.
    """
    return HTTPException(status_code=409, detail=error_detail(error))


################################# UNUSED BELOW

## FLAVORS


@authed.get(FLAVORS, response_model=List[FlavorWrapper])
async def flavors() -> List[FlavorWrapper]:
    """Get all flavors.

    Returns:
        All flavors.
    """
    return zen_store.flavors


@authed.post(
    FLAVORS,
    response_model=FlavorWrapper,
    responses={409: error_response},
)
async def create_flavor(flavor: FlavorWrapper) -> FlavorWrapper:
    """Creates a flavor.

    # noqa: DAR401

    Args:
        flavor: Flavor to create.

    Returns:
        The created flavor.
    """
    try:
        return zen_store.create_flavor(
            name=flavor.name,
            source=flavor.source,
            stack_component_type=flavor.type,
        )
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.get(
    FLAVORS + "/{component_type}/{name}", responses={404: error_response}
)
async def get_flavor_by_type_and_name(
    component_type: StackComponentType, name: str
) -> FlavorWrapper:
    """Returns a flavor of a given type and name.

    Args:
        component_type: Type of the component
        name: Name of the flavor.

    Returns:
        The requested flavor.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_flavor_by_name_and_type(
            component_type=component_type, flavor_name=name
        )
    except KeyError as error:
        raise not_found(error) from error


#### TEAMS


@authed.get(TEAMS, response_model=List[Team])
async def teams() -> List[Team]:
    """Returns all teams.

    Returns:
        All teams.
    """
    return zen_store.teams


@authed.get(TEAMS + "/{name}", responses={404: error_response})
async def get_team(name: str) -> Team:
    """Gets a specific team.

    Args:
        name: Name of the team.

    Returns:
        The requested team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    TEAMS,
    response_model=Team,
    responses={409: error_response},
)
async def create_team(team: Team) -> Team:
    """Creates a team.

    Args:
        team: Team to create.

    Returns:
        The created team.

    Raises:
        conflict: when the team already exists
    """
    try:
        return zen_store.create_team(team.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(TEAMS + "/{name}", responses={404: error_response})
async def delete_team(name: str) -> None:
    """Deletes a team.

    Args:
        name: Name of the team.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    TEAMS + "/{name}/users",
    response_model=List[User],
    responses={404: error_response},
)
async def users_for_team(name: str) -> List[User]:
    """Returns all users for a team.

    Args:
        name: Name of the team.

    Returns:
        All users for the team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_users_for_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(TEAMS + "/{name}/users", responses={404: error_response})
async def add_user_to_team(name: str, user: User) -> None:
    """Adds a user to a team.

    Args:
        name: Name of the team.
        user: User to add to the team.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.add_user_to_team(team_name=name, user_name=user.name)
    except KeyError as error:
        raise not_found(error) from error


@authed.delete(
    TEAMS + "/{team_name}/users/{user_name}", responses={404: error_response}
)
async def remove_user_from_team(team_name: str, user_name: str) -> None:
    """Removes a user from a team.

    Args:
        team_name: Name of the team.
        user_name: Name of the user.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.remove_user_from_team(
            team_name=team_name, user_name=user_name
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    TEAMS + "/{name}/role_assignments",
    response_model=List[RoleAssignment],
    responses={404: error_response},
)
async def role_assignments_for_team(
    name: str, project_name: Optional[str] = None
) -> List[RoleAssignment]:
    """Gets all role assignments for a team.

    Args:
        name: Name of the team.
        project_name: Name of the project.

    Returns:
        All role assignments for the team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role_assignments_for_team(
            team_name=name, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error


# include the router after all commands have been added to it so FastAPI
# recognizes them
app.include_router(authed)


# @authed.get("/", response_model=ProfileConfiguration)
# async def service_info() -> ProfileConfiguration:
#     """Returns the profile configuration for this service.

#     Returns:
#         Profile configuration for this service.
#     """
#     return profile


# NOT PART OF SWAGGER DOCS DESCRIBED
# @authed.get(
#     PIPELINE_RUNS + "/{pipeline_name}/{run_name}",
#     response_model=PipelineRunWrapper,
#     responses={404: error_response},
# )
# async def pipeline_run(
#     pipeline_name: str, run_name: str, project_name: Optional[str] = None
# ) -> PipelineRunWrapper:
#     """Returns a single pipeline run.

#     Args:
#         pipeline_name: Name of the pipeline.
#         run_name: Name of the run.
#         project_name: Name of the project.

#     Returns:
#         The requested pipeline run.

#     Raises:
#         not_found: when none are found.
#     """
#     try:
#         return zen_store.get_pipeline_run_wrapper(
#             pipeline_name=pipeline_name,
#             run_name=run_name,
#             project_name=project_name,
#         )
#     except KeyError as error:
#         raise not_found(error) from error


# @authed.get(STACKS_EMPTY, response_model=bool)
# async def stacks_empty() -> bool:
#     """Returns whether stacks are registered or not.

#     Returns:
#         True if there are no stacks registered, False otherwise.
#     """
#     return zen_store.stacks_empty


@authed.get(
    USERS + "/{name}/teams",
    response_model=List[Team],
    responses={404: error_response},
)
async def teams_for_user(name: str) -> List[Team]:
    """Returns all teams for a user.

    Args:
        name: Name of the user.

    Returns:
        All teams for the user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_teams_for_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error
