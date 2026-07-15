#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Management and public intake endpoints for webhook integrations."""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Security,
    status,
)
from fastapi.responses import Response
from pydantic import SecretStr
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers

from zenml.constants import (
    API,
    VERSION_1,
    WEBHOOKS,
)
from zenml.enums import WebhookType
from zenml.models import (
    Page,
    WebhookEventStatsUpdate,
    WebhookIntegrationCreateResponse,
    WebhookIntegrationFilter,
    WebhookIntegrationRequest,
    WebhookIntegrationResponse,
    WebhookIntegrationRotateSecretRequest,
    WebhookIntegrationSecretResponse,
    WebhookIntegrationUpdate,
)
from zenml.utils.secret_utils import (
    is_secret_reference,
    parse_secret_reference,
)
from zenml.webhooks import (
    WebhookAuthenticationError,
    WebhookPayloadError,
    get_webhook_adapter,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    async_handle_endpoint_errors,
    make_dependable,
    zen_store,
)

management_router = APIRouter(
    prefix=API + VERSION_1 + WEBHOOKS,
    tags=["webhooks"],
    responses={401: error_response, 403: error_response},
)

intake_router = APIRouter(
    prefix=API + VERSION_1 + WEBHOOKS,
    tags=["webhooks"],
)


def _verify_webhook_secret_reference_access(
    secret: SecretStr | None,
) -> None:
    """Verify access to a referenced ZenML secret value.

    Args:
        secret: A direct signing secret or ZenML secret reference.
    """
    if secret is None or not is_secret_reference(secret):
        return

    reference = parse_secret_reference(secret)
    referenced_secret = zen_store().get_secret_by_name_or_id(reference.name)
    verify_permission_for_model(
        model=referenced_secret, action=Action.READ_SECRET_VALUE
    )


@management_router.post("")
@async_fastapi_endpoint_wrapper
def create_webhook(
    integration: WebhookIntegrationRequest,
    _: AuthContext = Security(authorize),
) -> WebhookIntegrationCreateResponse:
    """Create a project-scoped webhook.

    Args:
        integration: The webhook creation request.

    Returns:
        The created integration and any generated signing secret.
    """
    verify_permission_for_model(model=integration, action=Action.CREATE)
    _verify_webhook_secret_reference_access(integration.secret)
    return zen_store().create_webhook_integration(integration)


@management_router.get("")
@async_fastapi_endpoint_wrapper
def list_webhooks(
    filter_model: WebhookIntegrationFilter = Depends(
        make_dependable(WebhookIntegrationFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[WebhookIntegrationResponse]:
    """List webhooks.

    Args:
        filter_model: The webhook filters.
        hydrate: Whether to include intake statistics.

    Returns:
        A page of webhooks.
    """
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.WEBHOOK_INTEGRATION,
        list_method=zen_store().list_webhook_integrations,
        hydrate=hydrate,
    )


@management_router.get("/{webhook_id}")
@async_fastapi_endpoint_wrapper
def get_webhook(
    webhook_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> WebhookIntegrationResponse:
    """Get a webhook.

    Args:
        webhook_id: The webhook ID.
        hydrate: Whether to include intake statistics.

    Returns:
        The webhook.
    """
    return verify_permissions_and_get_entity(
        id=webhook_id,
        get_method=zen_store().get_webhook_integration,
        hydrate=hydrate,
    )


@management_router.put("/{webhook_id}")
@async_fastapi_endpoint_wrapper
def update_webhook(
    webhook_id: UUID,
    update: WebhookIntegrationUpdate,
    _: AuthContext = Security(authorize),
) -> WebhookIntegrationResponse:
    """Update a webhook.

    Args:
        webhook_id: The webhook ID.
        update: The webhook update.

    Returns:
        The updated webhook.
    """
    integration = zen_store().get_webhook_integration(
        webhook_id, hydrate=False
    )
    verify_permission_for_model(model=integration, action=Action.UPDATE)
    _verify_webhook_secret_reference_access(update.secret)
    updated_integration = zen_store().update_webhook_integration(
        integration_id=integration.id,
        update=update,
    )
    return dehydrate_response_model(updated_integration)


@management_router.delete("/{webhook_id}")
@async_fastapi_endpoint_wrapper
def delete_webhook(
    webhook_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a webhook and its signing secret.

    Args:
        webhook_id: The webhook ID.
    """
    verify_permissions_and_delete_entity(
        id=webhook_id,
        get_method=zen_store().get_webhook_integration,
        delete_method=zen_store().delete_webhook_integration,
    )


@management_router.put("/{webhook_id}/secret")
@async_fastapi_endpoint_wrapper
def rotate_webhook_secret(
    webhook_id: UUID,
    request: WebhookIntegrationRotateSecretRequest,
    _: AuthContext = Security(authorize),
) -> WebhookIntegrationSecretResponse:
    """Rotate a webhook signing secret.

    Args:
        webhook_id: The webhook ID.
        request: The secret rotation request.

    Returns:
        The newly active signing secret.
    """
    integration = zen_store().get_webhook_integration(webhook_id)
    verify_permission_for_model(model=integration, action=Action.UPDATE)
    return zen_store().rotate_webhook_integration_secret(
        integration_id=webhook_id, request=request
    )


@intake_router.post(
    "/{webhook_type}/{webhook_id}/events",
    status_code=status.HTTP_202_ACCEPTED,
)
@async_handle_endpoint_errors
async def receive_webhook_event(
    webhook_type: WebhookType,
    webhook_id: UUID,
    request: Request,
) -> Response:
    """Authenticate and accept a provider webhook event.

    Args:
        webhook_type: The provider type from the public endpoint path.
        webhook_id: The webhook ID.
        request: The raw HTTP request.

    Returns:
        An empty accepted response.
    """
    body = await request.body()
    return await run_in_threadpool(
        _receive_webhook_event,
        webhook_type=webhook_type,
        integration_id=webhook_id,
        body=body,
        headers=request.headers,
    )


def _receive_webhook_event(
    webhook_type: WebhookType,
    integration_id: UUID,
    body: bytes,
    headers: Headers,
) -> Response:
    """Synchronously authenticate and accept a webhook event.

    Args:
        webhook_type: The provider type from the public endpoint path.
        integration_id: The webhook ID.
        body: The raw request body.
        headers: The request headers.

    Returns:
        An empty accepted response.

    Raises:
        HTTPException: If the integration cannot accept the event or the
            request fails authentication or payload validation.
    """
    try:
        integration = zen_store().get_webhook_integration(integration_id)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    if integration.webhook_type != webhook_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    secret = zen_store().get_webhook_integration_secret(integration_id)
    adapter = get_webhook_adapter(webhook_type)

    try:
        adapter.authenticate(body=body, headers=headers, secret=secret)
    except WebhookAuthenticationError as error:
        if integration.active:
            zen_store().record_webhook_event(
                integration_id,
                WebhookEventStatsUpdate(
                    auth_failed=True, error_summary=str(error)
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook authentication.",
        ) from error

    if not integration.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook integration is inactive.",
        )

    try:
        adapter.parse(body=body, headers=headers)
    except WebhookPayloadError as error:
        zen_store().record_webhook_event(
            integration_id,
            WebhookEventStatsUpdate(
                invalid_payload=True, error_summary=str(error)
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    zen_store().record_webhook_event(
        integration_id, WebhookEventStatsUpdate(accepted=True)
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
