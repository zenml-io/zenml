"""Endpoint definitions for comprehensive prompt management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse

from zenml.constants import (
    API,
    PROMPT_DEPLOYMENTS,
    PROMPT_EVALUATIONS,
    PROMPT_EXPERIMENTS,
    PROMPT_TEMPLATES,
    VERSION_1,
)
from zenml.models import (
    Page,
    PromptDeploymentFilter,
    PromptDeploymentRequest,
    PromptDeploymentResponse,
    PromptEvaluationFilter,
    PromptEvaluationRequest,
    PromptEvaluationResponse,
    PromptExperimentFilter,
    PromptExperimentRequest,
    PromptExperimentResponse,
    PromptExperimentUpdate,
    PromptTemplateFilter,
    PromptTemplateRequest,
    PromptTemplateResponse,
    PromptTemplateUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

# Create routers for each prompt management entity
prompt_templates_router = APIRouter(
    prefix=API + VERSION_1 + PROMPT_TEMPLATES,
    tags=["prompt_templates"],
    responses={401: error_response, 403: error_response},
)

prompt_experiments_router = APIRouter(
    prefix=API + VERSION_1 + PROMPT_EXPERIMENTS,
    tags=["prompt_experiments"],
    responses={401: error_response, 403: error_response},
)

prompt_evaluations_router = APIRouter(
    prefix=API + VERSION_1 + PROMPT_EVALUATIONS,
    tags=["prompt_evaluations"],
    responses={401: error_response, 403: error_response},
)

prompt_deployments_router = APIRouter(
    prefix=API + VERSION_1 + PROMPT_DEPLOYMENTS,
    tags=["prompt_deployments"],
    responses={401: error_response, 403: error_response},
)


# ==================== PROMPT TEMPLATES ====================


@prompt_templates_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_prompt_templates(
    template_filter_model: PromptTemplateFilter = Depends(
        make_dependable(PromptTemplateFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[PromptTemplateResponse]:
    """List prompt templates with filtering.

    Args:
        template_filter_model: Filter model for templates.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Page of prompt template responses.
    """
    return verify_permissions_and_list_entities(
        filter_model=template_filter_model,
        resource_type=ResourceType.ARTIFACT,  # Using artifact as base type
        list_method=zen_store().list_prompt_templates,
        hydrate=hydrate,
    )


@prompt_templates_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
    status_code=201,
)
@async_fastapi_endpoint_wrapper
def create_prompt_template(
    template: PromptTemplateRequest,
    auth_context: AuthContext = Security(authorize),
) -> PromptTemplateResponse:
    """Create a new prompt template.

    Args:
        template: Prompt template request model.
        auth_context: Authentication context.

    Returns:
        Created prompt template response.
    """
    return verify_permissions_and_create_entity(
        request_model=template,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_prompt_template,
    )


@prompt_templates_router.get(
    "/{template_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_template(
    template_id: UUID,
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> PromptTemplateResponse:
    """Get a specific prompt template.

    Args:
        template_id: ID of the prompt template.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Prompt template response.
    """
    return verify_permissions_and_get_entity(
        id=template_id,
        get_method=zen_store().get_prompt_template,
        hydrate=hydrate,
    )


@prompt_templates_router.put(
    "/{template_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_prompt_template(
    template_id: UUID,
    template_update: PromptTemplateUpdate,
    auth_context: AuthContext = Security(authorize),
) -> PromptTemplateResponse:
    """Update a prompt template.

    Args:
        template_id: ID of the prompt template.
        template_update: Template update model.
        auth_context: Authentication context.

    Returns:
        Updated prompt template response.
    """
    return verify_permissions_and_update_entity(
        id=template_id,
        update_model=template_update,
        get_method=zen_store().get_prompt_template,
        update_method=zen_store().update_prompt_template,
    )


@prompt_templates_router.delete(
    "/{template_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_prompt_template(
    template_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> None:
    """Delete a prompt template.

    Args:
        template_id: ID of the prompt template.
        auth_context: Authentication context.
    """
    verify_permissions_and_delete_entity(
        id=template_id,
        get_method=zen_store().get_prompt_template,
        delete_method=zen_store().delete_prompt_template,
    )


@prompt_templates_router.post(
    "/{template_id}/versions",
    responses={401: error_response, 404: error_response, 422: error_response},
    status_code=201,
)
@async_fastapi_endpoint_wrapper
def create_prompt_template_version(
    template_id: UUID,
    template: PromptTemplateRequest,
    auth_context: AuthContext = Security(authorize),
) -> PromptTemplateResponse:
    """Create a new version of a prompt template.

    Args:
        template_id: ID of the prompt template.
        template: Updated template content.
        auth_context: Authentication context.

    Returns:
        New prompt template version response.
    """
    return verify_permissions_and_create_entity(
        request_model=template,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_prompt_template_version,
        template_id=template_id,
    )


@prompt_templates_router.get(
    "/{template_id}/compare/{version_a}/{version_b}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def compare_prompt_template_versions(
    template_id: UUID,
    version_a: str,
    version_b: str,
    auth_context: AuthContext = Security(authorize),
) -> JSONResponse:
    """Compare two versions of a prompt template.

    Args:
        template_id: ID of the prompt template.
        version_a: First version to compare.
        version_b: Second version to compare.
        auth_context: Authentication context.

    Returns:
        JSON response with comparison data.
    """
    comparison = zen_store().compare_prompt_template_versions(
        template_id=template_id,
        version_a=version_a,
        version_b=version_b,
    )
    return JSONResponse(content=comparison)


# ==================== PROMPT EXPERIMENTS ====================


@prompt_experiments_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_prompt_experiments(
    experiment_filter_model: PromptExperimentFilter = Depends(
        make_dependable(PromptExperimentFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[PromptExperimentResponse]:
    """List prompt experiments with filtering.

    Args:
        experiment_filter_model: Filter model for experiments.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Page of prompt experiment responses.
    """
    return verify_permissions_and_list_entities(
        filter_model=experiment_filter_model,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_prompt_experiments,
        hydrate=hydrate,
    )


@prompt_experiments_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
    status_code=201,
)
@async_fastapi_endpoint_wrapper
def create_prompt_experiment(
    experiment: PromptExperimentRequest,
    auth_context: AuthContext = Security(authorize),
) -> PromptExperimentResponse:
    """Create a new prompt experiment.

    Args:
        experiment: Prompt experiment request model.
        auth_context: Authentication context.

    Returns:
        Created prompt experiment response.
    """
    return verify_permissions_and_create_entity(
        request_model=experiment,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_prompt_experiment,
    )


@prompt_experiments_router.get(
    "/{experiment_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_experiment(
    experiment_id: UUID,
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> PromptExperimentResponse:
    """Get a specific prompt experiment.

    Args:
        experiment_id: ID of the prompt experiment.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Prompt experiment response.
    """
    return verify_permissions_and_get_entity(
        id=experiment_id,
        get_method=zen_store().get_prompt_experiment,
        hydrate=hydrate,
    )


@prompt_experiments_router.put(
    "/{experiment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_prompt_experiment(
    experiment_id: UUID,
    experiment_update: PromptExperimentUpdate,
    auth_context: AuthContext = Security(authorize),
) -> PromptExperimentResponse:
    """Update a prompt experiment.

    Args:
        experiment_id: ID of the prompt experiment.
        experiment_update: Experiment update model.
        auth_context: Authentication context.

    Returns:
        Updated prompt experiment response.
    """
    return verify_permissions_and_update_entity(
        id=experiment_id,
        update_model=experiment_update,
        get_method=zen_store().get_prompt_experiment,
        update_method=zen_store().update_prompt_experiment,
    )


@prompt_experiments_router.delete(
    "/{experiment_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_prompt_experiment(
    experiment_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> None:
    """Delete a prompt experiment.

    Args:
        experiment_id: ID of the prompt experiment.
        auth_context: Authentication context.
    """
    verify_permissions_and_delete_entity(
        id=experiment_id,
        get_method=zen_store().get_prompt_experiment,
        delete_method=zen_store().delete_prompt_experiment,
    )


# ==================== PROMPT EVALUATIONS ====================


@prompt_evaluations_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_prompt_evaluations(
    evaluation_filter_model: PromptEvaluationFilter = Depends(
        make_dependable(PromptEvaluationFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[PromptEvaluationResponse]:
    """List prompt evaluations with filtering.

    Args:
        evaluation_filter_model: Filter model for evaluations.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Page of prompt evaluation responses.
    """
    return verify_permissions_and_list_entities(
        filter_model=evaluation_filter_model,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_prompt_evaluations,
        hydrate=hydrate,
    )


@prompt_evaluations_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
    status_code=201,
)
@async_fastapi_endpoint_wrapper
def create_prompt_evaluation(
    evaluation: PromptEvaluationRequest,
    auth_context: AuthContext = Security(authorize),
) -> PromptEvaluationResponse:
    """Create a new prompt evaluation.

    Args:
        evaluation: Prompt evaluation request model.
        auth_context: Authentication context.

    Returns:
        Created prompt evaluation response.
    """
    return verify_permissions_and_create_entity(
        request_model=evaluation,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_prompt_evaluation,
    )


@prompt_evaluations_router.get(
    "/{evaluation_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_evaluation(
    evaluation_id: UUID,
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> PromptEvaluationResponse:
    """Get a specific prompt evaluation.

    Args:
        evaluation_id: ID of the prompt evaluation.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Prompt evaluation response.
    """
    return verify_permissions_and_get_entity(
        id=evaluation_id,
        get_method=zen_store().get_prompt_evaluation,
        hydrate=hydrate,
    )


# ==================== PROMPT DEPLOYMENTS ====================


@prompt_deployments_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_prompt_deployments(
    deployment_filter_model: PromptDeploymentFilter = Depends(
        make_dependable(PromptDeploymentFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[PromptDeploymentResponse]:
    """List prompt deployments with filtering.

    Args:
        deployment_filter_model: Filter model for deployments.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Page of prompt deployment responses.
    """
    return verify_permissions_and_list_entities(
        filter_model=deployment_filter_model,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_prompt_deployments,
        hydrate=hydrate,
    )


@prompt_deployments_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
    status_code=201,
)
@async_fastapi_endpoint_wrapper
def create_prompt_deployment(
    deployment: PromptDeploymentRequest,
    auth_context: AuthContext = Security(authorize),
) -> PromptDeploymentResponse:
    """Create a new prompt deployment.

    Args:
        deployment: Prompt deployment request model.
        auth_context: Authentication context.

    Returns:
        Created prompt deployment response.
    """
    return verify_permissions_and_create_entity(
        request_model=deployment,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_prompt_deployment,
    )


@prompt_deployments_router.get(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_deployment(
    deployment_id: UUID,
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> PromptDeploymentResponse:
    """Get a specific prompt deployment.

    Args:
        deployment_id: ID of the prompt deployment.
        hydrate: Whether to hydrate the response.
        auth_context: Authentication context.

    Returns:
        Prompt deployment response.
    """
    return verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=zen_store().get_prompt_deployment,
        hydrate=hydrate,
    )


@prompt_deployments_router.put(
    "/{deployment_id}/rollback",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def rollback_prompt_deployment(
    deployment_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> PromptDeploymentResponse:
    """Rollback a prompt deployment to previous version.

    Args:
        deployment_id: ID of the prompt deployment.
        auth_context: Authentication context.

    Returns:
        Updated prompt deployment response.
    """
    return zen_store().rollback_prompt_deployment(deployment_id)
