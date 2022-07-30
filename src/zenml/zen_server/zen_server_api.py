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
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    ENV_ZENML_PROFILE_NAME,
    FLAVORS,
    PIPELINE_RUNS,
    PROJECTS,
    ROLE_ASSIGNMENTS,
    ROLES,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
    STACKS_EMPTY,
    STORE_ASSOCIATIONS,
    TEAMS,
    USERS,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.repository import Repository
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import (
    ComponentWrapper,
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    StackWrapper,
    StoreAssociation,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

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
authed = APIRouter(
    dependencies=[Depends(authorize)], responses={401: error_response}
)


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


@authed.get("/", response_model=ProfileConfiguration)
async def service_info() -> ProfileConfiguration:
    """Returns the profile configuration for this service.

    Returns:
        Profile configuration for this service.
    """
    return profile


@app.head("/health")
@app.get("/health")
async def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


@authed.get(STACKS_EMPTY, response_model=bool)
async def stacks_empty() -> bool:
    """Returns whether stacks are registered or not.

    Returns:
        True if there are no stacks registered, False otherwise.
    """
    return zen_store.stacks_empty


@authed.get(
    STACK_CONFIGURATIONS + "/{name}",
    response_model=Dict[StackComponentType, str],
    responses={404: error_response},
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    """Returns the configuration for the requested stack.

    Args:
        name: Name of the stack.

    Returns:
        Configuration for the requested stack.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack_configuration(name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    STACK_CONFIGURATIONS,
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    """Returns configurations for all stacks.

    Returns:
        Configurations for all stacks.
    """
    return zen_store.stack_configurations


@authed.post(STACK_COMPONENTS, responses={409: error_response})
async def register_stack_component(
    component: ComponentWrapper,
) -> None:
    """Registers a stack component.

    Args:
        component: Stack component to register.

    Raises:
        conflict: when the component already exists.
    """
    try:
        zen_store.register_stack_component(component)
    except StackComponentExistsError as error:
        raise conflict(error) from error


@authed.delete(STACKS + "/{name}", responses={404: error_response})
async def deregister_stack(name: str) -> None:
    """Deregisters a stack.

    Args:
        name: Name of the stack to deregister.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.deregister_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(STACKS, response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    """Returns all stacks.

    Returns:
        All stacks.
    """
    return zen_store.stacks


@authed.get(
    STACKS + "/{name}",
    response_model=StackWrapper,
    responses={404: error_response},
)
async def get_stack(name: str) -> StackWrapper:
    """Returns the requested stack.

    Args:
        name: Name of the stack.

    Returns:
        The requested stack.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    STACKS,
    responses={409: error_response},
)
async def register_stack(stack: StackWrapper) -> None:
    """Registers a stack.

    Args:
        stack: Stack to register.

    Raises:
        conflict: when a stack with the same name is already registered
    """
    try:
        zen_store.register_stack(stack)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error


@authed.put(
    STACKS + "/{name}",
    responses={404: error_response},
)
async def update_stack(stack: StackWrapper, name: str) -> None:
    """Updates a stack.

    Args:
        stack: Stack to update.
        name: Name of the stack.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.update_stack(name, stack)
    except DoesNotExistException as error:
        raise not_found(error) from error


@authed.put(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=Dict[str, str],
    responses={404: error_response},
)
async def update_stack_component(
    name: str,
    component_type: StackComponentType,
    component: ComponentWrapper,
) -> Dict[str, str]:
    """Updates a stack component.

    Args:
        name: Name of the stack component.
        component_type: Type of the stack component.
        component: Stack component to update.

    Returns:
        Updated stack component.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.update_stack_component(name, component_type, component)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=ComponentWrapper,
    responses={404: error_response},
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> ComponentWrapper:
    """Returns the requested stack component.

    Args:
        component_type: Type of the stack component.
        name: Name of the stack component.

    Returns:
        The requested stack component.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentWrapper],
)
async def get_stack_components(
    component_type: StackComponentType,
) -> List[ComponentWrapper]:
    """Returns all stack components for the requested type.

    Args:
        component_type: Type of the stack components.

    Returns:
        All stack components for the requested type.
    """
    return zen_store.get_stack_components(component_type)


@authed.delete(
    STACK_COMPONENTS + "/{component_type}/{name}",
    responses={404: error_response, 409: error_response},
)
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    """Deregisters a stack component.

    Args:
        component_type: Type of the stack component.
        name: Name of the stack component.

    Returns:
        None

    Raises:
        not_found: when none are found
        conflict: when the stack component is still in use
    """
    try:
        return zen_store.deregister_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise conflict(error) from error


@authed.get(USERS, response_model=List[User])
async def users() -> List[User]:
    """Returns all users.

    Returns:
        All users.
    """
    return zen_store.users


@authed.get(USERS + "/{name}", responses={404: error_response})
async def get_user(name: str) -> User:
    """Gets a specific user.

    Args:
        name: Name of the user.

    Returns:
        The requested user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    USERS,
    response_model=User,
    responses={409: error_response},
)
async def create_user(user: User) -> User:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.

    Returns:
        The created user.
    """
    try:
        return zen_store.create_user(user.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(USERS + "/{name}", responses={404: error_response})
async def delete_user(name: str) -> None:
    """Deletes a user.

    Args:
        name: Name of the user.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


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


@authed.get(
    USERS + "/{name}/role_assignments",
    response_model=List[RoleAssignment],
    responses={404: error_response},
)
async def role_assignments_for_user(
    name: str, project_name: Optional[str] = None
) -> List[RoleAssignment]:
    """Returns all role assignments for a user.

    Args:
        name: Name of the user.
        project_name: Name of the project.

    Returns:
        All role assignments for the user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role_assignments_for_user(
            user_name=name, project_name=project_name, include_team_roles=False
        )
    except KeyError as error:
        raise not_found(error) from error


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


@authed.get(PROJECTS, response_model=List[Project])
async def projects() -> List[Project]:
    """Returns all projects.

    Returns:
        All projects.
    """
    return zen_store.projects


@authed.get(
    PROJECTS + "/{project_name}",
    response_model=Project,
    responses={404: error_response},
)
async def get_project(project_name: str) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        The requested project.
    """
    try:
        return zen_store.get_project(project_name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    PROJECTS,
    response_model=Project,
    responses={409: error_response},
)
async def create_project(project: Project) -> Project:
    """Creates a project.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.
    """
    try:
        return zen_store.create_project(
            project_name=project.name, description=project.description
        )
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(PROJECTS + "/{name}", responses={404: error_response})
async def delete_project(name: str) -> None:
    """Deletes a project.

    Args:
        name: Name of the project.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_project(project_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(ROLES, response_model=List[Role])
async def roles() -> List[Role]:
    """Returns all roles.

    Returns:
        All roles.
    """
    return zen_store.roles


@authed.get(ROLES + "/{name}", responses={404: error_response})
async def get_role(name: str) -> Role:
    """Gets a specific role.

    Args:
        name: Name of the role.

    Returns:
        The requested role.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role(role_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    ROLES,
    response_model=Role,
    responses={409: error_response},
)
async def create_role(role: Role) -> Role:
    """Creates a role.

    # noqa: DAR401

    Args:
        role: Role to create.

    Returns:
        The created role.
    """
    try:
        return zen_store.create_role(role.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(ROLES + "/{name}", responses={404: error_response})
async def delete_role(name: str) -> None:
    """Deletes a role.

    Args:
        name: Name of the role.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_role(role_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(ROLE_ASSIGNMENTS, response_model=List[RoleAssignment])
async def role_assignments() -> List[RoleAssignment]:
    """Returns all role assignments.

    Returns:
        All role assignments.
    """
    return zen_store.role_assignments


@authed.get(STORE_ASSOCIATIONS, response_model=List[StoreAssociation])
async def store_associations() -> List[StoreAssociation]:
    """Returns all store associations.

    Returns:
        All store associations.
    """
    return zen_store.store_associations


@authed.delete(
    STORE_ASSOCIATIONS + "/{artifact_store_uuid}/{metadata_store_uuid}",
    responses={404: error_response},
)
async def delete_store_association(
    artifact_store_uuid: UUID,
    metadata_store_uuid: UUID,
) -> None:
    """Deletes a store association.

    Args:
        artifact_store_uuid: The UUID of the selected artifact store.
        metadata_store_uuid: The UUID of the selected metadata store.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_store_association_for_artifact_and_metadata_store(
            artifact_store_uuid=artifact_store_uuid,
            metadata_store_uuid=metadata_store_uuid,
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    ROLE_ASSIGNMENTS,
    responses={404: error_response},
)
async def assign_role(data: Dict[str, Any]) -> None:
    """Assigns a role.

    Args:
        data: Data containing the role assignment.

    Raises:
        not_found: when none are found
    """
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.assign_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.delete(ROLE_ASSIGNMENTS, responses={404: error_response})
async def revoke_role(data: Dict[str, Any]) -> None:
    """Revokes a role.

    Args:
        data: Data containing the role assignment.

    Raises:
        not_found: when none are found
    """
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.revoke_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    PIPELINE_RUNS + "/{pipeline_name}", response_model=List[PipelineRunWrapper]
)
async def pipeline_runs(
    pipeline_name: str, project_name: Optional[str] = None
) -> List[PipelineRunWrapper]:
    """Returns all runs for a pipeline.

    Args:
        pipeline_name: Name of the pipeline.
        project_name: Name of the project.

    Returns:
        All runs for a pipeline.
    """
    return zen_store.get_pipeline_runs(
        pipeline_name=pipeline_name, project_name=project_name
    )


@authed.get(
    PIPELINE_RUNS + "/{pipeline_name}/{run_name}",
    response_model=PipelineRunWrapper,
    responses={404: error_response},
)
async def pipeline_run(
    pipeline_name: str, run_name: str, project_name: Optional[str] = None
) -> PipelineRunWrapper:
    """Returns a single pipeline run.

    Args:
        pipeline_name: Name of the pipeline.
        run_name: Name of the run.
        project_name: Name of the project.

    Returns:
        The requested pipeline run.

    Raises:
        not_found: when none are found.
    """
    try:
        return zen_store.get_pipeline_run(
            pipeline_name=pipeline_name,
            run_name=run_name,
            project_name=project_name,
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    PIPELINE_RUNS,
    responses={409: error_response},
)
async def register_pipeline_run(pipeline_run: PipelineRunWrapper) -> None:
    """Registers a pipeline run.

    # noqa: DAR401

    Args:
        pipeline_run: Pipeline run to register.

    Returns:
        None
    """
    try:
        return zen_store.register_pipeline_run(pipeline_run)
    except EntityExistsError as error:
        raise conflict(error) from error


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


@authed.get(FLAVORS + "/{component_type}", responses={404: error_response})
async def get_flavor_by_type(
    component_type: StackComponentType,
) -> List[FlavorWrapper]:
    """Returns all flavors of a given type.

    Args:
        component_type: Type of the component.

    Returns:
        The requested flavors.

    Raises:
        not_found: when none are found.
    """
    try:
        return zen_store.get_flavors_by_type(component_type=component_type)
    except KeyError as error:
        raise not_found(error) from error


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


# include the router after all commands have been added to it so FastAPI
# recognizes them
app.include_router(authed)
