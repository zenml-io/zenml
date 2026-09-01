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
"""Management and public intake endpoints for webhooks."""

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
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers

from zenml.constants import (
    API,
    VERSION_1,
    WEBHOOKS,
)
from zenml.dispatcher import EventDispatcher
from zenml.models import (
    Page,
    WebhookCreateResponse,
    WebhookEventStatsUpdate,
    WebhookFilter,
    WebhookRequest,
    WebhookResponse,
    WebhookRotateSecretRequest,
    WebhookSecretResponse,
    WebhookUpdate,
)
from zenml.webhooks import (
    WebhookAuthenticationError,
    WebhookEvent,
    WebhookPayloadError,
    WebhookPreValidationResult,
    get_webhook_provider,
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
    server_config,
    zen_store,
)


def _set_webhook_endpoint_url(webhook: WebhookResponse) -> None:
    """Set the externally reachable intake URL on a webhook response.

    Args:
        webhook: The response to enrich before API serialization.
    """
    server_api_url = server_config().server_api_url
    webhook.get_body().endpoint_url = (
        f"{server_api_url}{WEBHOOKS}/{webhook.webhook_type}/{webhook.id}/events"
        if server_api_url
        else None
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


@management_router.post("")
@async_fastapi_endpoint_wrapper
def create_webhook(
    webhook: WebhookRequest,
    _: AuthContext = Security(authorize),
) -> WebhookCreateResponse:
    """Create a project-scoped webhook.

    Args:
        webhook: The webhook creation request.

    Returns:
        The created webhook and any generated signing secret.

    Raises:
        HTTPException: If the webhook provider type is unsupported.
    """
    try:
        get_webhook_provider(webhook.webhook_type)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported webhook type: {webhook.webhook_type}.",
        ) from error

    verify_permission_for_model(model=webhook, action=Action.CREATE)
    result = zen_store().create_webhook(webhook)
    _set_webhook_endpoint_url(result)
    return dehydrate_response_model(result)


@management_router.get("")
@async_fastapi_endpoint_wrapper
def list_webhooks(
    filter_model: WebhookFilter = Depends(make_dependable(WebhookFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[WebhookResponse]:
    """List webhooks.

    Args:
        filter_model: The webhook filters.
        hydrate: Whether to include intake statistics.

    Returns:
        A page of webhooks.
    """
    webhooks = verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.WEBHOOK,
        list_method=zen_store().list_webhooks,
        hydrate=hydrate,
    )
    for webhook in webhooks.items:
        _set_webhook_endpoint_url(webhook)
    return webhooks


@management_router.get("/{webhook_id}")
@async_fastapi_endpoint_wrapper
def get_webhook(
    webhook_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> WebhookResponse:
    """Get a webhook.

    Args:
        webhook_id: The webhook ID.
        hydrate: Whether to include intake statistics.

    Returns:
        The webhook.
    """
    webhook = verify_permissions_and_get_entity(
        id=webhook_id,
        get_method=zen_store().get_webhook,
        hydrate=hydrate,
    )
    _set_webhook_endpoint_url(webhook)
    return webhook


@management_router.put("/{webhook_id}")
@async_fastapi_endpoint_wrapper
def update_webhook(
    webhook_id: UUID,
    update: WebhookUpdate,
    _: AuthContext = Security(authorize),
) -> WebhookResponse:
    """Update a webhook.

    Args:
        webhook_id: The webhook ID.
        update: The webhook update.

    Returns:
        The updated webhook.
    """
    webhook = zen_store().get_webhook(webhook_id, hydrate=False)
    verify_permission_for_model(model=webhook, action=Action.UPDATE)
    updated_webhook = zen_store().update_webhook(
        webhook_id=webhook.id,
        update=update,
    )
    _set_webhook_endpoint_url(updated_webhook)
    return dehydrate_response_model(updated_webhook)


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
        get_method=zen_store().get_webhook,
        delete_method=zen_store().delete_webhook,
    )


@management_router.put("/{webhook_id}/secret")
@async_fastapi_endpoint_wrapper
def rotate_webhook_secret(
    webhook_id: UUID,
    request: WebhookRotateSecretRequest,
    _: AuthContext = Security(authorize),
) -> WebhookSecretResponse:
    """Rotate a webhook signing secret.

    Args:
        webhook_id: The webhook ID.
        request: The secret rotation request.

    Returns:
        The newly active signing secret.
    """
    webhook = zen_store().get_webhook(webhook_id)
    verify_permission_for_model(model=webhook, action=Action.UPDATE)
    return zen_store().rotate_webhook_secret(
        webhook_id=webhook_id, request=request
    )


@intake_router.post(
    "/{webhook_type}/{webhook_id}/events",
    status_code=status.HTTP_202_ACCEPTED,
)
@async_handle_endpoint_errors
async def receive_webhook_event(
    webhook_type: str,
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

    Raises:
        HTTPException: If required provider metadata is malformed.
    """
    try:
        provider = get_webhook_provider(webhook_type)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    try:
        result = await provider.pre_validate(headers=request.headers)
    except WebhookPayloadError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    if result == WebhookPreValidationResult.IGNORE:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    body = await request.body()
    return await run_in_threadpool(
        _receive_webhook_event,
        webhook_type=webhook_type,
        webhook_id=webhook_id,
        body=body,
        headers=request.headers,
    )


def _receive_webhook_event(
    webhook_type: str,
    webhook_id: UUID,
    body: bytes,
    headers: Headers,
) -> Response:
    """Synchronously authenticate and accept a webhook event.

    Args:
        webhook_type: The provider type from the public endpoint path.
        webhook_id: The webhook ID.
        body: The raw request body.
        headers: The request headers.

    Returns:
        An empty accepted response.

    Raises:
        HTTPException: If the webhook cannot accept the event or the
            request fails authentication or payload validation.
    """
    try:
        config = zen_store().get_webhook_intake_config(
            webhook_id,
            expected_webhook_type=webhook_type,
        )
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    provider = get_webhook_provider(webhook_type)

    try:
        provider.authenticate(
            body=body,
            headers=headers,
            secret=config.secret.get_secret_value(),
        )
    except WebhookAuthenticationError as error:
        if config.active:
            zen_store().record_webhook_event(
                webhook_id,
                WebhookEventStatsUpdate(
                    auth_failed=True, error_summary=str(error)
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook authentication.",
        ) from error

    if not config.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook is inactive.",
        )

    try:
        parsed_event = provider.parse(body=body, headers=headers)
    except WebhookPayloadError as error:
        zen_store().record_webhook_event(
            webhook_id,
            WebhookEventStatsUpdate(
                invalid_payload=True, error_summary=str(error)
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    zen_store().record_webhook_event(
        webhook_id, WebhookEventStatsUpdate(accepted=True)
    )
    event = WebhookEvent(
        project_id=config.project_id,
        webhook_id=webhook_id,
        webhook_type=webhook_type,
        event_type=parsed_event.event_type,
        delivery_id=parsed_event.delivery_id,
        payload=parsed_event.payload,
    )
    EventDispatcher().dispatch_event(event)
    return Response(status_code=status.HTTP_202_ACCEPTED)
