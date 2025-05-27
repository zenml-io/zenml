#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for code repositories."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.constants import (
    API,
    DEVICE_VERIFY,
    DEVICES,
    VERSION_1,
)
from zenml.enums import OAuthDeviceStatus, OnboardingStep
from zenml.models import (
    OAuthDeviceFilter,
    OAuthDeviceInternalUpdate,
    OAuthDeviceResponse,
    OAuthDeviceUpdate,
    OAuthDeviceVerificationRequest,
    Page,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + DEVICES,
    tags=["authorized_devices"],
    responses={401: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_authorized_devices(
    filter_model: OAuthDeviceFilter = Depends(
        make_dependable(OAuthDeviceFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[OAuthDeviceResponse]:
    """Gets a page of OAuth2 authorized devices belonging to the current user.

    Args:
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: The current auth context.

    Returns:
        Page of OAuth2 authorized device objects.
    """
    filter_model.set_scope_user(auth_context.user.id)
    return zen_store().list_authorized_devices(
        filter_model=filter_model, hydrate=hydrate
    )


@router.get(
    "/{device_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_authorization_device(
    device_id: UUID,
    user_code: Optional[str] = None,
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> OAuthDeviceResponse:
    """Gets a specific OAuth2 authorized device using its unique ID.

    Args:
        device_id: The ID of the OAuth2 authorized device to get.
        user_code: The user code of the OAuth2 authorized device to get. Needs
            to be specified with devices that have not been verified yet.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: The current auth context.

    Returns:
        A specific OAuth2 authorized device object.

    Raises:
        KeyError: If the device with the given ID does not exist, does not
            belong to the current user or could not be verified using the
            given user code.
    """
    device = zen_store().get_authorized_device(
        device_id=device_id, hydrate=hydrate
    )
    if not device.user_id:
        # A device that hasn't been verified and associated with a user yet
        # can only be retrieved if the user code is specified and valid.
        if user_code:
            internal_device = zen_store().get_internal_authorized_device(
                device_id=device_id, hydrate=hydrate
            )
            if internal_device.verify_user_code(user_code=user_code):
                return device
    elif device.user_id == auth_context.user.id:
        return device

    raise KeyError(
        f"Unable to get device with ID {device_id}: No device with "
        "this ID found."
    )


@router.put(
    "/{device_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_authorized_device(
    device_id: UUID,
    update: OAuthDeviceUpdate,
    auth_context: AuthContext = Security(authorize),
) -> OAuthDeviceResponse:
    """Updates a specific OAuth2 authorized device using its unique ID.

    Args:
        device_id: The ID of the OAuth2 authorized device to update.
        update: The model containing the attributes to update.
        auth_context: The current auth context.

    Returns:
        The updated OAuth2 authorized device object.

    Raises:
        KeyError: If the device with the given ID does not exist or does not
            belong to the current user.
    """
    device = zen_store().get_authorized_device(device_id=device_id)
    if not device.user_id or device.user_id != auth_context.user.id:
        raise KeyError(
            f"Unable to get device with ID {device_id}: No device with "
            "this ID found."
        )

    return zen_store().update_authorized_device(
        device_id=device_id, update=update
    )


@router.put(
    "/{device_id}" + DEVICE_VERIFY,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def verify_authorized_device(
    device_id: UUID,
    request: OAuthDeviceVerificationRequest,
    auth_context: AuthContext = Security(authorize),
) -> OAuthDeviceResponse:
    """Verifies a specific OAuth2 authorized device using its unique ID.

    This endpoint implements the OAuth2 device authorization grant flow as
    defined in https://tools.ietf.org/html/rfc8628. It is called to verify
    the user code for a given device ID.

    If the user code is valid, the device is marked as verified and associated
    with the user that authorized the device. This association is required to
    be able to issue access tokens or revoke the device later on.

    Args:
        device_id: The ID of the OAuth2 authorized device to update.
        request: The model containing the verification request.
        auth_context: The current auth context.

    Returns:
        The updated OAuth2 authorized device object.

    Raises:
        ValueError: If the device verification request fails.
    """
    config = server_config()
    store = zen_store()

    # Check if a device is registered for the ID
    device_model = store.get_internal_authorized_device(
        device_id=device_id,
    )

    with track_handler(event=AnalyticsEvent.DEVICE_VERIFIED):
        # Check if the device is in a state that allows verification.
        if device_model.status != OAuthDeviceStatus.PENDING:
            raise ValueError(
                "Invalid request: device not pending verification.",
            )

        # Check if the device verification has expired.
        if device_model.expires and device_model.expires < utc_now():
            raise ValueError(
                "Invalid request: device verification expired.",
            )

        # Check if the device already has a user associated with it. If so, the
        # current user and the user associated with the device must be the same.
        if (
            device_model.user_id
            and device_model.user_id != auth_context.user.id
        ):
            raise ValueError(
                "Invalid request: this device is associated with another user.",
            )

        # Check if the device code is valid.
        if not device_model.verify_user_code(request.user_code):
            # If the device code is invalid, increment the failed auth attempts
            # counter and lock the device if the maximum number of failed auth
            # attempts has been reached.
            failed_auth_attempts = device_model.failed_auth_attempts + 1
            update = OAuthDeviceInternalUpdate(
                failed_auth_attempts=failed_auth_attempts
            )
            if failed_auth_attempts >= config.max_failed_device_auth_attempts:
                update.locked = True
            store.update_internal_authorized_device(
                device_id=device_model.id,
                update=update,
            )
            if failed_auth_attempts >= config.max_failed_device_auth_attempts:
                raise ValueError(
                    "Invalid request: device locked due to too many failed "
                    "authentication attempts.",
                )
            raise ValueError(
                "Invalid request: invalid user code.",
            )

        # If the device code is valid, associate the device with the current user.
        # We don't reset the expiration date yet, because we want to make sure
        # that the client has received the access token before we do so, to avoid
        # brute force attacks on the device code.
        update = OAuthDeviceInternalUpdate(
            status=OAuthDeviceStatus.VERIFIED,
            user_id=auth_context.user.id,
            failed_auth_attempts=0,
            trusted_device=request.trusted_device,
        )
        device_model = store.update_internal_authorized_device(
            device_id=device_model.id,
            update=update,
        )

    store.update_onboarding_state(
        completed_steps={OnboardingStep.DEVICE_VERIFIED}
    )
    return device_model


@router.delete(
    "/{device_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_authorized_device(
    device_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific OAuth2 authorized device using its unique ID.

    Args:
        device_id: The ID of the OAuth2 authorized device to delete.
        auth_context: The current auth context.

    Raises:
        KeyError: If the device with the given ID does not exist or does not
            belong to the current user.
    """
    device = zen_store().get_authorized_device(device_id=device_id)
    if not device.user_id or device.user_id != auth_context.user.id:
        raise KeyError(
            f"Unable to get device with ID {device_id}: No device with "
            "this ID found."
        )

    zen_store().delete_authorized_device(device_id=device_id)
