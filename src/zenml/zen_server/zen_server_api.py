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


from fastapi import FastAPI

import zenml
from zenml.zen_server.routers import (
    auth_endpoints,
    flavors_endpoints,
    metadata_config_endpoints,
    pipelines_endpoints,
    projects_endpoints,
    roles_endpoints,
    runs_endpoints,
    stack_components_endpoints,
    stacks_endpoints,
    steps_endpoints,
    users_endpoints,
)

app = FastAPI(title="ZenML", version=zenml.__version__)

# Basic Health Endpoint
@app.head("/health", include_in_schema=False)
@app.get("/health")
async def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


# to run this file locally, execute:
# uvicorn zenml.zen_server.zen_server_api:app --reload


app.include_router(auth_endpoints.router)
app.include_router(metadata_config_endpoints.router)
app.include_router(pipelines_endpoints.router)
app.include_router(projects_endpoints.router)
app.include_router(flavors_endpoints.router)
app.include_router(roles_endpoints.router)
app.include_router(runs_endpoints.router)
app.include_router(stacks_endpoints.router)
app.include_router(stack_components_endpoints.router)
app.include_router(steps_endpoints.router)
app.include_router(users_endpoints.router)
app.include_router(users_endpoints.activation_router)
# For future use

# app.include_router(repositories_endpoints.router)
# app.include_router(triggers_endpoints.router)
################################# UNUSED BELOW
#
# ## FLAVORS
#
#
# @authed.get(FLAVORS, response_model=List[FlavorModel])
# async def flavors() -> List[FlavorModel]:
#     """Get all flavors.
#
#     Returns:
#         All flavors.
#     """
#     return zen_store.flavors
#
#
# @authed.post(
#     FLAVORS,
#     response_model=FlavorModel,
#     responses={409: error_response},
# )
# async def create_flavor(flavor: FlavorModel) -> FlavorModel:
#     """Creates a flavor.
#
#     # noqa: DAR401
#
#     Args:
#         flavor: Flavor to create.
#
#     Returns:
#         The created flavor.
#     """
#     try:
#         return zen_store.create_flavor(
#             name=flavor.name,
#             source=flavor.source,
#             stack_component_type=flavor.type,
#         )
#     except EntityExistsError as error:
#         raise conflict(error) from error
#
#
# @authed.get(
#     FLAVORS + "/{component_type}/{name}", responses={404: error_response}
# )
# async def get_flavor_by_type_and_name(
#     component_type: StackComponentType, name: str
# ) -> FlavorModel:
#     """Returns a flavor of a given type and name.
#
#     Args:
#         component_type: Type of the component
#         name: Name of the flavor.
#
#     Returns:
#         The requested flavor.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_flavor_by_name_and_type(
#             component_type=component_type, flavor_name=name
#         )
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# #### TEAMS
#
#
# @authed.get(TEAMS, response_model=List[Team])
# async def teams() -> List[Team]:
#     """Returns all teams.
#
#     Returns:
#         All teams.
#     """
#     return zen_store.teams
#
#
# @authed.get(TEAMS + "/{name}", responses={404: error_response})
# async def get_team(name: str) -> Team:
#     """Gets a specific team.
#
#     Args:
#         name: Name of the team.
#
#     Returns:
#         The requested team.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_team(team_name=name)
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# @authed.post(
#     TEAMS,
#     response_model=Team,
#     responses={409: error_response},
# )
# async def create_team(team: Team) -> Team:
#     """Creates a team.
#
#     Args:
#         team: Team to create.
#
#     Returns:
#         The created team.
#
#     Raises:
#         conflict: when the team already exists
#     """
#     try:
#         return zen_store.create_team(team.name)
#     except EntityExistsError as error:
#         raise conflict(error) from error
#
#
# @authed.delete(TEAMS + "/{name}", responses={404: error_response})
# async def delete_team(name: str) -> None:
#     """Deletes a team.
#
#     Args:
#         name: Name of the team.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         zen_store.delete_team(team_name=name)
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# @authed.get(
#     TEAMS + "/{name}/users",
#     response_model=List[User],
#     responses={404: error_response},
# )
# async def users_for_team(name: str) -> List[User]:
#     """Returns all users for a team.
#
#     Args:
#         name: Name of the team.
#
#     Returns:
#         All users for the team.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_users_for_team(team_name=name)
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# @authed.post(TEAMS + "/{name}/users", responses={404: error_response})
# async def add_user_to_team(name: str, user: User) -> None:
#     """Adds a user to a team.
#
#     Args:
#         name: Name of the team.
#         user: User to add to the team.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         zen_store.add_user_to_team(team_name=name, user_name=user.name)
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# @authed.delete(
#     TEAMS + "/{team_name}/users/{user_name}", responses={404: error_response}
# )
# async def remove_user_from_team(team_name: str, user_name: str) -> None:
#     """Removes a user from a team.
#
#     Args:
#         team_name: Name of the team.
#         user_name: Name of the user.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         zen_store.remove_user_from_team(
#             team_name=team_name, user_name=user_name
#         )
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# @authed.get(
#     TEAMS + "/{name}/role_assignments",
#     response_model=List[RoleAssignment],
#     responses={404: error_response},
# )
# async def role_assignments_for_team(
#     name: str, project_name: Optional[str] = None
# ) -> List[RoleAssignment]:
#     """Gets all role assignments for a team.
#
#     Args:
#         name: Name of the team.
#         project_name: Name of the project.
#
#     Returns:
#         All role assignments for the team.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_role_assignments_for_team(
#             team_name=name, project_name=project_name
#         )
#     except KeyError as error:
#         raise not_found(error) from error
#
#
# # include the router after all commands have been added to it so FastAPI
# # recognizes them
# app.include_router(authed)
#
#
# # @authed.get("/", response_model=ProfileConfiguration)
# # async def service_info() -> ProfileConfiguration:
# #     """Returns the profile configuration for this service.
#
# #     Returns:
# #         Profile configuration for this service.
# #     """
# #     return profile
#
#
# # NOT PART OF SWAGGER DOCS DESCRIBED
# # @authed.get(
# #     PIPELINE_RUNS + "/{pipeline_name}/{run_name}",
# #     response_model=PipelineRunModel,
# #     responses={404: error_response},
# # )
# # async def pipeline_run(
# #     pipeline_name: str, run_name: str, project_name: Optional[str] = None
# # ) -> PipelineRunModel:
# #     """Returns a single pipeline run.
#
# #     Args:
# #         pipeline_name: Name of the pipeline.
# #         run_name: Name of the run.
# #         project_name: Name of the project.
#
# #     Returns:
# #         The requested pipeline run.
#
# #     Raises:
# #         not_found: when none are found.
# #     """
# #     try:
# #         return zen_store.get_pipeline_run_wrapper(
# #             pipeline_name=pipeline_name,
# #             run_name=run_name,
# #             project_name=project_name,
# #         )
# #     except KeyError as error:
# #         raise not_found(error) from error
#
#
# # @authed.get(STACKS_EMPTY, response_model=bool)
# # async def stacks_empty() -> bool:
# #     """Returns whether stacks are registered or not.
#
# #     Returns:
# #         True if there are no stacks registered, False otherwise.
# #     """
# #     return zen_store.stacks_empty
#
#
# @authed.get(
#     USERS + "/{name}/teams",
#     response_model=List[Team],
#     responses={404: error_response},
# )
# async def teams_for_user(name: str) -> List[Team]:
#     """Returns all teams for a user.
#
#     Args:
#         name: Name of the user.
#
#     Returns:
#         All teams for the user.
#
#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_teams_for_user(user_name=name)
#     except KeyError as error:
#         raise not_found(error) from error
