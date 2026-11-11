"""Authorized managed-model intents; provider work runs asynchronously."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Security

from zenml.enums import StackComponentType
from zenml.models.managed_model import (
    ManagedModelAdmission,
    ManagedModelMutation,
    ManagedModelRevisionRequest,
    ManagedModelService,
    ManagedModelServicePage,
    ManagedModelServiceRequest,
    ModelArtifactReference,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    get_allowed_resource_ids,
    verify_permission,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix="/api/v1/managed-model-services", tags=["managed-model-services"]
)


def _check_enabled() -> None:
    if not server_config().managed_model_services_enabled:
        raise HTTPException(404, "Managed model services are not enabled.")
    if not server_config().managed_model_serving_profiles:
        raise HTTPException(
            503, "Managed serving has no configured runtime profiles."
        )


def _get_authorized(service_id: UUID, action: Action) -> ManagedModelService:
    service = zen_store().managed_models.get(service_id)
    verify_permission(
        ResourceType.MANAGED_MODEL_SERVICE,
        action,
        resource_id=service.id,
        project_id=service.project_id,
    )
    return service


def _authorize_revision(
    revision: ManagedModelRevisionRequest, project_id: UUID
) -> None:
    if (
        revision.serving_profile
        not in server_config().managed_model_serving_profiles
    ):
        raise HTTPException(422, "Unknown managed serving profile.")
    package = revision.package
    references = [package.model, package.tokenizer]
    if package.kind == "peft_lora":
        references.append(package.base_model)
    for reference in references:
        if not isinstance(reference, ModelArtifactReference):
            continue
        artifact = zen_store().get_artifact_version(
            reference.artifact_version_id
        )
        if artifact.project_id != project_id:
            raise HTTPException(
                403, "Model artifacts must belong to the service project."
            )
        verify_permission(
            ResourceType.ARTIFACT_VERSION,
            Action.READ,
            resource_id=artifact.id,
            project_id=project_id,
        )
        if artifact.artifact_store_id is None:
            raise HTTPException(422, "Model artifact has no artifact store.")
        store = zen_store().get_stack_component(artifact.artifact_store_id)
        verify_permission(
            ResourceType.STACK_COMPONENT, Action.READ, resource_id=store.id
        )
        if store.connector is None:
            raise HTTPException(
                422, "Managed serving requires a connected artifact store."
            )
        verify_permission(
            ResourceType.SERVICE_CONNECTOR,
            Action.CLIENT,
            resource_id=store.connector.id,
        )


@router.post("", status_code=202)
@async_fastapi_endpoint_wrapper(deduplicate=False)
def create_managed_model_service(
    request: ManagedModelServiceRequest,
    request_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ],
    _: AuthContext = Security(authorize),
) -> ManagedModelService:
    """Authorize and durably accept model creation without provider side effects.

    Args:
        request: Package and component references in one project.
        request_key: Stable identity reused when retrying this intent.

    Returns:
        Accepted service and operation.

    Raises:
        HTTPException: If the selected component is not a managed deployer.
    """
    _check_enabled()
    verify_permission(
        ResourceType.MANAGED_MODEL_SERVICE,
        Action.CREATE,
        project_id=request.project_id,
    )
    zen_store().get_project(request.project_id)
    component = zen_store().get_stack_component(request.model_deployer_id)
    verify_permission(
        ResourceType.STACK_COMPONENT, Action.READ, resource_id=component.id
    )
    if (
        component.type != StackComponentType.MODEL_DEPLOYER
        or component.flavor != "managed"
    ):
        raise HTTPException(422, "Select a managed model-deployer component.")
    _authorize_revision(request, request.project_id)
    return zen_store().managed_models.create(request, request_key)


@router.get("")
@async_fastapi_endpoint_wrapper
def list_managed_model_services(
    project_id: UUID,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    _: AuthContext = Security(authorize),
) -> ManagedModelServicePage:
    """List only authorized services in an explicit project.

    Args:
        project_id: Project to query.
        offset: Page offset.
        limit: Maximum page size.

    Returns:
        A page filtered before counting and pagination.
    """
    _check_enabled()
    allowed_ids = get_allowed_resource_ids(
        ResourceType.MANAGED_MODEL_SERVICE, project_id=project_id
    )
    return zen_store().managed_models.list(
        project_id, offset, limit, allowed_ids
    )


@router.get("/{service_id}")
@async_fastapi_endpoint_wrapper
def get_managed_model_service(
    service_id: UUID,
    _: AuthContext = Security(authorize),
) -> ManagedModelService:
    """Read authorized progress and retained revision metadata.

    Args:
        service_id: Stable service ID.

    Returns:
        Public service state.
    """
    _check_enabled()
    return _get_authorized(service_id, Action.READ)


@router.post("/{service_id}/operations", status_code=202)
@async_fastapi_endpoint_wrapper(deduplicate=False)
def mutate_managed_model_service(
    service_id: UUID,
    request: ManagedModelMutation,
    request_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ],
    _: AuthContext = Security(authorize),
) -> ManagedModelService:
    """Accept an authorized update, rollback, pause, resume or deletion.

    Args:
        service_id: Stable service ID.
        request: Lifecycle intent against an observed generation.
        request_key: Stable identity reused when retrying this intent.

    Returns:
        Accepted service and operation.

    Raises:
        HTTPException: If a rollback revision is not retained by this service.
    """
    _check_enabled()
    action = Action.DELETE if request.action == "delete" else Action.UPDATE
    service = _get_authorized(service_id, action)
    revision: Optional[ManagedModelRevisionRequest] = request.revision
    if request.action in ("rollback", "resume"):
        target = (
            request.revision_id
            if request.action == "rollback"
            else service.active_revision_id
        )
        revision = next(
            (item for item in service.revisions if item.id == target), None
        )
        if revision is None:
            raise HTTPException(422, "Requested revision is not retained.")
    if revision is not None:
        _authorize_revision(revision, service.project_id)
    return zen_store().managed_models.mutate(service_id, request, request_key)


@router.delete("/{service_id}", status_code=202)
@async_fastapi_endpoint_wrapper
def delete_managed_model_service(
    service_id: UUID,
    expected_generation: Annotated[int, Query(ge=1)],
    request_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ],
    _: AuthContext = Security(authorize),
) -> ManagedModelService:
    """Accept cleanup intent while retaining the service record.

    Args:
        service_id: Stable service ID.
        expected_generation: Last observed generation.
        request_key: Stable identity reused when retrying this intent.

    Returns:
        Accepted deletion operation.
    """
    _check_enabled()
    _get_authorized(service_id, Action.DELETE)
    return zen_store().managed_models.mutate(
        service_id,
        ManagedModelMutation(
            action="delete", expected_generation=expected_generation
        ),
        request_key,
    )


@router.get("/{service_id}/authorize")
@async_fastapi_endpoint_wrapper
def authorize_managed_model_inference(
    service_id: UUID,
    generation: Annotated[int, Query(ge=1)],
    _: AuthContext = Security(authorize),
) -> ManagedModelAdmission:
    """Authorize an exact serving generation through existing workspace identity.

    Args:
        service_id: Inference service selected by the trusted route.
        generation: Generation observed by the route reconciler.

    Returns:
        Authorized service and active revision identifiers.

    Raises:
        HTTPException: If admission is closed or the route generation is stale.
    """
    _check_enabled()
    service = _get_authorized(service_id, Action.INVOKE)
    if (
        service.desired_state != "running"
        or service.state != "ready"
        or service.active_revision_id is None
    ):
        raise HTTPException(
            403, "Inference admission is closed for this service."
        )
    if service.generation != generation:
        raise HTTPException(409, "Inference route generation is stale.")
    return ManagedModelAdmission(
        service_id=service.id,
        generation=service.generation,
        revision_id=service.active_revision_id,
    )
