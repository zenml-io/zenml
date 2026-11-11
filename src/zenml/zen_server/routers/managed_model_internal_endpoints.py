"""Operation-scoped capabilities for protected managed-model workers."""

import secrets
from datetime import timezone
from typing import Annotated, Optional
from urllib.parse import urlsplit
from uuid import UUID

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Response,
    Security,
)

from zenml.exceptions import IllegalOperationError
from zenml.managed_models.state import (
    ManagedModelAssignment,
    ManagedModelCheckpoint,
    ManagedModelInferenceTarget,
    ManagedModelLease,
    ManagedModelResult,
    ManagedModelSource,
)
from zenml.models.managed_model import ModelArtifactReference
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix="/api/v1/internal/managed-model-services", include_in_schema=False
)


def _get_key() -> str:
    key = server_config().managed_model_controller_key
    if key is None or len(key.get_secret_value()) < 32:
        raise HTTPException(503, "Managed execution is not configured.")
    return key.get_secret_value()


def _authorize_controller(
    authorization: Annotated[Optional[str], Header()] = None,
) -> None:
    if not secrets.compare_digest(authorization or "", "Bearer " + _get_key()):
        raise HTTPException(401, "Invalid controller identity.")


def _authorize_worker(
    operation_id: UUID,
    authorization: Annotated[Optional[str], Header()] = None,
) -> ManagedModelLease:
    try:
        scheme, token = (authorization or "").split(" ", 1)
        if scheme != "Bearer":
            raise ValueError("Invalid scheme")
        claims = jwt.decode(
            token,
            _get_key(),
            algorithms=["HS256"],
            audience="zenml-managed-model-worker",
            issuer=str(server_config().get_external_server_id()),
            options={"require": ["exp", "sub", "lease_id", "iss", "aud"]},
        )
        if claims["sub"] != "operation:" + str(operation_id):
            raise ValueError("Wrong operation")
        return zen_store().managed_models.get_claim(
            operation_id, UUID(claims["lease_id"])
        )
    except (ValueError, jwt.InvalidTokenError, IllegalOperationError):
        raise HTTPException(
            401, "Worker identity expired or no longer owns this operation."
        ) from None


@router.post("/claim", dependencies=[Depends(_authorize_controller)])
@async_fastapi_endpoint_wrapper(deduplicate=False)
def claim_managed_model_operation(
    response: Response,
) -> Optional[ManagedModelAssignment]:
    """Issue a bounded capability for one durably claimed operation.

    Args:
        response: HTTP response carrying private cache controls.

    Returns:
        One assignment, or None when the queue is empty.
    """
    response.headers["Cache-Control"] = "no-store"
    lease = zen_store().managed_models.claim(lease_seconds=300)
    if lease is None:
        return None
    token = jwt.encode(
        {
            "sub": "operation:" + str(lease.operation_id),
            "lease_id": str(lease.lease_id),
            "iss": str(server_config().get_external_server_id()),
            "aud": "zenml-managed-model-worker",
            "exp": lease.expires_at.replace(tzinfo=timezone.utc),
        },
        _get_key(),
        algorithm="HS256",
    )
    return ManagedModelAssignment(lease=lease, token=token)


@router.get("/{operation_id}")
@async_fastapi_endpoint_wrapper
def get_managed_model_assignment(
    lease: Annotated[ManagedModelLease, Depends(_authorize_worker)],
) -> ManagedModelLease:
    """Read only the operation bound to this worker identity.

    Args:
        lease: Authenticated durable assignment.

    Returns:
        Current assignment, including recovery evidence.
    """
    return lease


@router.put("/{operation_id}/checkpoint")
@async_fastapi_endpoint_wrapper
def checkpoint_managed_model_operation(
    checkpoint: ManagedModelCheckpoint,
    lease: Annotated[ManagedModelLease, Depends(_authorize_worker)],
) -> None:
    """Persist recovery identifiers before the next external side effect.

    Args:
        checkpoint: Private recovery evidence without credentials.
        lease: Authenticated durable assignment.
    """
    zen_store().managed_models.checkpoint(lease, checkpoint)


@router.put("/{operation_id}/result")
@async_fastapi_endpoint_wrapper
def finish_managed_model_operation(
    result: ManagedModelResult,
    lease: Annotated[ManagedModelLease, Depends(_authorize_worker)],
) -> None:
    """Commit observations without permitting changes to the accepted intent.

    Args:
        result: Mutable observations for the assigned service.
        lease: Authenticated durable assignment.

    Raises:
        HTTPException: If the result references an unassigned revision or URL.
    """
    service = lease.service.model_copy(deep=True)
    revisions = {str(item.id) for item in service.revisions}
    expected_url = server_config().managed_model_inference_url
    if expected_url:
        expected_url = expected_url.rstrip("/") + "/" + str(service.id)
    if (
        not set(result.resources).issubset(revisions)
        or (
            result.active_revision_id is not None
            and str(result.active_revision_id) not in revisions
        )
        or (
            result.prediction_url is not None
            and result.prediction_url != expected_url
        )
        or (
            result.serving_generation is not None
            and result.serving_generation
            not in (service.serving_generation, service.generation)
        )
        or (
            result.state == "deleted"
            and (service.desired_state != "deleted" or result.resources)
        )
        or (
            result.state == "ready"
            and (
                result.active_revision_id is None
                or result.prediction_url is None
            )
        )
    ):
        raise HTTPException(
            422, "Observation does not match the assigned service."
        )
    service.state = result.state
    service.active_revision_id = result.active_revision_id
    service.serving_generation = result.serving_generation
    service.prediction_url = result.prediction_url
    service.operation.status = result.status
    service.operation.error = result.error
    zen_store().managed_models.finish(lease, service, result.resources)


@router.post("/{operation_id}/source", response_model=ManagedModelSource)
@async_fastapi_endpoint_wrapper(deduplicate=False)
def get_managed_model_source_credentials(
    reference: ModelArtifactReference,
    response: Response,
    lease: Annotated[ManagedModelLease, Depends(_authorize_worker)],
) -> ManagedModelSource:
    """Resolve connector credentials only for an assigned package dependency.

    Args:
        reference: Exact artifact-relative reference in the accepted package.
        response: HTTP response carrying private cache controls.
        lease: Authenticated durable assignment.

    Returns:
        Existing connector client credentials for the assigned S3 bucket.

    Raises:
        HTTPException: If the source is not assigned, available or compatible.
    """
    response.headers["Cache-Control"] = "no-store"
    revision = next(
        (
            item
            for item in lease.service.revisions
            if item.id == lease.target_revision_id
        ),
        None,
    )
    if revision is None or lease.service.operation.action in (
        "pause",
        "delete",
    ):
        raise HTTPException(403, "Operation has no assigned model source.")
    package = revision.package
    references = [package.model, package.tokenizer]
    if package.kind == "peft_lora":
        references.append(package.base_model)
    if reference not in references:
        raise HTTPException(
            403, "Source is not part of the assigned revision."
        )
    source = next(
        (
            item
            for item in lease.sources
            if item.artifact_version_id == reference.artifact_version_id
        ),
        None,
    )
    if source is None:
        raise HTTPException(
            403, "Source binding is not retained by this operation."
        )
    uri = urlsplit(source.uri)
    if uri.scheme != "s3" or not uri.netloc:
        raise HTTPException(422, "Source requires an existing S3 connector.")
    # This uses the existing connector delegation. It does not narrow the AWS
    # credential itself; the POC intentionally preserves that connector scope.
    try:
        connector = zen_store().get_service_connector_client(
            source.connector_id,
            resource_type="s3-bucket",
            resource_id=uri.netloc,
        )
    except Exception:
        raise HTTPException(
            503, "Assigned source credentials are unavailable."
        ) from None
    return ManagedModelSource(uri=source.uri, connector=connector)


@router.get("/inference/{service_id}")
@async_fastapi_endpoint_wrapper
def resolve_managed_inference(
    service_id: UUID,
    proxy_key: Annotated[str, Header(alias="X-ZenML-Managed-Proxy-Key")],
    response: Response,
    _: AuthContext = Security(authorize),
) -> ManagedModelInferenceTarget:
    """Authorize the original caller before releasing a private routing target.

    Args:
        service_id: Stable service selected by the public path.
        proxy_key: Separate identity held only by the internal inference proxy.
        response: HTTP response carrying private cache controls.

    Returns:
        Exact active deployment with admission checked in the same store read.

    Raises:
        HTTPException: If the proxy identity or feature is unavailable.
    """
    key = server_config().managed_model_proxy_key
    if key is None or not secrets.compare_digest(
        proxy_key, key.get_secret_value()
    ):
        raise HTTPException(401, "Invalid inference proxy identity.")
    if not server_config().managed_model_services_enabled:
        raise HTTPException(403, "Managed inference is not enabled.")
    response.headers["Cache-Control"] = "no-store"
    service = zen_store().managed_models.get(service_id)
    verify_permission(
        ResourceType.MANAGED_MODEL_SERVICE,
        Action.INVOKE,
        resource_id=service.id,
        project_id=service.project_id,
    )
    return zen_store().managed_models.get_inference_target(service_id)
