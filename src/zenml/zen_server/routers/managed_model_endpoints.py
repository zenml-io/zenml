"""Authorized managed-model intents; provider work runs asynchronously."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Response, Security

from zenml.enums import StackComponentType
from zenml.managed_models.state import ManagedModelDependency
from zenml.models.managed_model import (
    ManagedModelInferenceSecret,
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
) -> list[ManagedModelDependency]:
    sources = []
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
        sources.append(
            ManagedModelDependency(
                artifact_version_id=artifact.id,
                artifact_store_id=store.id,
                connector_id=store.connector.id,
                uri=artifact.uri,
            )
        )
    return sources


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
        or component.flavor_name != "managed"
    ):
        raise HTTPException(422, "Select a managed model-deployer component.")
    verify_permission(ResourceType.SECRET, Action.CREATE)
    verify_permission(
        ResourceType.MANAGED_MODEL_SERVICE,
        Action.INVOKE,
        project_id=request.project_id,
    )
    sources = _authorize_revision(request, request.project_id)
    service = zen_store().managed_models.create(
        request, request_key, sources, wait_for_inference_key=True
    )
    try:
        zen_store().managed_inference_keys.ensure(service.id, _.user.id)
    except RuntimeError:
        raise HTTPException(
            503,
            f"Service {service.id} awaits secret storage; retry with the same Idempotency-Key.",
        ) from None
    return zen_store().managed_models.get(service.id)


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
    if request.action not in ("delete", "pause", "retry"):
        _check_enabled()
    action = Action.DELETE if request.action == "delete" else Action.UPDATE
    service = _get_authorized(service_id, action)
    if request.action == "retry":
        if service.operation.action == "delete":
            _get_authorized(service_id, Action.DELETE)
        else:
            _check_enabled()
            for retained in service.revisions:
                _authorize_revision(retained, service.project_id)
                for source in zen_store().managed_models.get_revision_sources(
                    service.id, retained.id
                ):
                    verify_permission(
                        ResourceType.SERVICE_CONNECTOR,
                        Action.CLIENT,
                        resource_id=source.connector_id,
                    )
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
    sources = (
        _authorize_revision(revision, service.project_id)
        if revision is not None
        else []
    )
    if request.action in ("rollback", "resume") and target is not None:
        for source in zen_store().managed_models.get_revision_sources(
            service.id, target
        ):
            verify_permission(
                ResourceType.SERVICE_CONNECTOR,
                Action.CLIENT,
                resource_id=source.connector_id,
            )
            verify_permission(
                ResourceType.STACK_COMPONENT,
                Action.READ,
                resource_id=source.artifact_store_id,
            )
    return zen_store().managed_models.mutate(
        service_id, request, request_key, sources
    )


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
    _get_authorized(service_id, Action.DELETE)
    return zen_store().managed_models.mutate(
        service_id,
        ManagedModelMutation(
            action="delete", expected_generation=expected_generation
        ),
        request_key,
    )


@router.post("/{service_id}/inference-key")
@async_fastapi_endpoint_wrapper(deduplicate=False)
def rotate_managed_model_inference_key(
    service_id: UUID,
    response: Response,
    _: AuthContext = Security(authorize),
) -> ManagedModelInferenceSecret:
    """Issue a new inference key, immediately replacing any previous key.

    Args:
        service_id: Target service.
        response: Response carrying private cache controls.

    Returns:
        Private ZenML secret reference containing the new key.
    """
    _check_enabled()
    _get_authorized(service_id, Action.UPDATE)
    _get_authorized(service_id, Action.INVOKE)
    response.headers["Cache-Control"] = "no-store"
    verify_permission(ResourceType.SECRET, Action.CREATE)
    return zen_store().managed_inference_keys.rotate(service_id, _.user.id)


@router.delete("/{service_id}/inference-key")
@async_fastapi_endpoint_wrapper(deduplicate=False)
def revoke_managed_model_inference_key(
    service_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Revoke inference access while preserving the deployment.

    Args:
        service_id: Target service.
    """
    _get_authorized(service_id, Action.UPDATE)
    zen_store().managed_inference_keys.revoke(service_id)


@router.delete("/{service_id}/record")
@async_fastapi_endpoint_wrapper
def purge_managed_model_service(
    service_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Purge a completed tombstone after provider cleanup has succeeded.

    Args:
        service_id: Stable identity of a fully deleted service.
    """
    _get_authorized(service_id, Action.DELETE)
    zen_store().managed_inference_keys.cleanup(service_id)
    zen_store().managed_models.purge(service_id)
