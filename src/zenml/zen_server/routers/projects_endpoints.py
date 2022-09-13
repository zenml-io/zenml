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
from typing import List, Union, Optional

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import (
    PIPELINES,
    PROJECTS,
    REPOSITORIES,
    STACK_COMPONENTS,
    STACKS,
    VERSION_1, FLAVORS,
)
from zenml.exceptions import (
    EntityExistsError,
    NotAuthorizedError,
    StackComponentExistsError,
    StackExistsError,
    ValidationError,
)
from zenml.models import (
    CodeRepositoryModel,
    ComponentModel,
    PipelineModel,
    ProjectModel,
    StackModel, FlavorModel,
)
from zenml.models.stack_models import HydratedStackModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.utils import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store
)

router = APIRouter(
    prefix=VERSION_1 + PROJECTS,
    tags=["projects"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[ProjectModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_projects() -> List[ProjectModel]:
    """Lists all projects in the organization.

    Returns:
        A list of projects.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_projects()
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/",
    response_model=ProjectModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_project(project: ProjectModel) -> ProjectModel:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.

    Raises:
        conflict: when project already exists
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_project(project=project)
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project(project_name_or_id: str) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        The requested project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project(
            project_name_or_id=parse_name_or_uuid(project_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_project(
    project_name_or_id: str, project: ProjectModel
) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to update.
        project: the project to use to update

    Returns:
        The updated project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_project(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            project=project,
        )
    except KeyError as error:
        raise not_found(error) from error
    # except NotAuthorizedError as error:
    #     raise HTTPException(status_code=401, detail=error_detail(error))
    # except KeyError as error:
    #     raise HTTPException(status_code=404, detail=error_detail(error))
    # except ValidationError as error:
    #     raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_project(project_name_or_id: str) -> None:
    """Deletes a project.

    Args:
        project_name_or_id: Name or ID of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_project(
            project_name_or_id=parse_name_or_uuid(project_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[List[HydratedStackModel], List[StackModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stacks(
    project_name_or_id: str,
    user_name_or_id: Optional[str] = None,
    stack_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = True
) -> Union[List[HydratedStackModel], List[StackModel]]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        stack_name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stacks part of the specified project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        stacks_list = zen_store.list_stacks(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            user_name_or_id=parse_name_or_uuid(user_name_or_id),
            is_shared=is_shared,
            name=stack_name)
        if hydrated:
            return [stack.to_hydrated_model() for stack in stacks_list]
        else:
            return stacks_list
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[HydratedStackModel, StackModel],
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack(
    project_name_or_id: str,
    stack: StackModel,
    hydrated: bool = True
) -> Union[HydratedStackModel, StackModel]:
    """Creates a stack for a particular project.

    Args:
        project_name_or_id: Name or ID of the project.
        stack: Stack to register.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The created stack.

    Raises:
        conflict: when an identical stack already exists
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        created_stack = zen_store.register_stack(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            stack=stack,
        )
        if hydrated:
            return created_stack.to_hydrated_model()
        else:
            return created_stack
    except (
        StackExistsError,
        StackComponentExistsError,
        EntityExistsError,
    ) as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_project_stack_components(
    project_name_or_id: str,
) -> List[ComponentModel]:
    """List stack components that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        All stack components part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_stack_components(
            project_name_or_id=parse_name_or_uuid(project_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_project_stack_components_by_type(
    component_type: str,
    project_name_or_id: str,
) -> List[ComponentModel]:
    """List stack components of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name_or_id: Name or ID of the project.

    Returns:
        All stack components of a certain type that are part of a project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_stack_components(
            type=component_type,
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=ComponentModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack_component(
    project_name_or_id: str,
    component: ComponentModel,
) -> None:
    """Creates a stack component.

    Args:
        project_name_or_id: Name or ID of the project.
        component: Stack component to register.

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.register_stack_component(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            component=component,
        )
    except StackComponentExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + FLAVORS,
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_project_flavors(
    project_name_or_id: Optional[str] = None,
    component_type: Optional[str] = None
) -> List[FlavorModel]:
    """List stack components flavors of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name_or_id: Name or ID of the project.

    Returns:
        All stack components of a certain type that are part of a project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        flavors_list = zen_store.list_flavors(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            component_type=component_type
        )
        return flavors_list
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name_or_id}" + FLAVORS,
    response_model=FlavorModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_flavor(
    project_name_or_id: str,
    flavor: FlavorModel,
) -> FlavorModel:
    """Creates a stack component flavor.

    Args:
        project_name_or_id: Name or ID of the project.
        flavor: Stack component flavor to register.

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        # TODO: [server] inject user here
        created_flavor = zen_store.create_flavor(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            flavor=flavor,
        )
        return created_flavor
    except StackComponentExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + PIPELINES,
    response_model=List[PipelineModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_pipelines(
    project_name_or_id: str,
) -> List[PipelineModel]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        All pipelines within the project.

    Raises:
        not_found: when the project does not exist.
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_pipelines(
            project_name_or_id=parse_name_or_uuid(project_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name_or_id}" + PIPELINES,
    response_model=PipelineModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_pipeline(
    project_name_or_id: str, pipeline: PipelineModel
) -> PipelineModel:
    """Creates a pipeline.

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline: Pipeline to create.

    Raises:
        conflict: when the pipeline already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_pipeline(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            pipeline=pipeline,
        )
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error
    except PipelineExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{project_name_or_id}" + REPOSITORIES,
    response_model=List[CodeRepositoryModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_repositories(
    project_name_or_id: str,
) -> List[CodeRepositoryModel]:
    """Gets repositories defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        All repositories within the project.

    Raises:
        not_found: when the project does not exist.
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_repositories(
            project_name_or_id=parse_name_or_uuid(project_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{project_name_or_id}" + REPOSITORIES,
    response_model=CodeRepositoryModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def connect_project_repository(
    project_name_or_id: str, repository: CodeRepositoryModel
) -> CodeRepositoryModel:
    """Attach or connect a repository to a project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        The connected repository.

    Raises:
        not_found: when the project does not exist.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.connect_project_repository(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            repository=repository,
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
