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
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import (
    PIPELINES,
    PROJECTS,
    REPOSITORIES,
    STACK_COMPONENTS,
    STACKS,
)
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.zen_server.utils import (
    authorize, error_detail, not_found, conflict, error_response, zen_store
)
from zenml.models import ComponentModel, Project, StackModel, \
    CodeRepositoryModel
from zenml.models import PipelineModel

router = APIRouter(
    prefix=PROJECTS,
    tags=["projects"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[Project],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_projects() -> List[Project]:
    """Lists all projects in the organization.

    Returns:
        A list of projects.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.projects
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/",
    response_model=Project,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_project(project: Project) -> Project:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_project(
            project_name=project.name, description=project.description
        )
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}",
    response_model=Project,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project(project_name: str) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        The requested project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{project_name}",
    response_model=Project,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_project(
        project_name: str, updated_project: Project
) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project to update.
        updated_project: the project to use to update

    Returns:
        The updated project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_project(project_name, updated_project)
    except KeyError as error:
        raise not_found(error) from error
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{project_name}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_project(project_name: str) -> None:
    """Deletes a project.

    Args:
        project_name: Name of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_project(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + STACKS,
    response_model=List[StackModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stacks(project_name: str) -> List[StackModel]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All stacks part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stacks(project_name=project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name}" + STACKS,
    response_model=StackModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack(project_name: str, stack: StackModel) -> StackModel:
    """Creates a stack for a particular project.

    Args:
        project_name: Name of the project.
        stack: Stack to register.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_stack(
            project_name, stack
        )  ## TODO: originally register_stack
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + STACK_COMPONENTS,
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stack_components(
        project_name: str,
) -> List[ComponentModel]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All stack components part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_stack_components(project_name=project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stack_components_by_type(
        component_type: str,
        project_name: str,
) -> List[ComponentModel]:
    """Get stack components of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name: Name of the project.

    Returns:
        All stack components of a certain type that are part of a project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_stack_components_by_type(
            component_type=component_type, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name}" + STACK_COMPONENTS + "/{component_type}",
    response_model=ComponentModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack_component_by_type(
        component_type: str,
        project_name: str,
        component: ComponentModel,
) -> None:
    """Creates a stack component.

    Args:
        component_type: Type of the component.
        project_name: Name of the project.
        component: Stack component to register.

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.create_stack_component_by_type(
            component_type, project_name, component
        )
    except StackComponentExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + PIPELINES,
    response_model=List[Project],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_pipelines(
        project_name: str,
) -> List[Project]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All pipelines within the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_pipelines(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name}" + PIPELINES,
    response_model=PipelineModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_pipeline(
        project_name: str, pipeline: PipelineModel
) -> PipelineModel:
    """Creates a pipeline.

    Args:
        project_name: Name of the project.
        pipeline: Pipeline to create.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_pipeline(project_name, pipeline)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + REPOSITORIES,
    response_model=List[CodeRepositoryModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_repositories(
        project_name: str,
) -> List[CodeRepositoryModel]:
    """Gets repositories defined for a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All repositories within the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_repositories(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name}" + REPOSITORIES,
    response_model=CodeRepositoryModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def connect_project_repository(
        project_name: str, repository: CodeRepositoryModel
) -> CodeRepositoryModel:
    """Attach or connect a repository to a project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        The connected repository.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.connect_project_repository(project_name, repository)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
