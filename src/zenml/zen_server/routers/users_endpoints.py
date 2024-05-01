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
"""Endpoint definitions for users."""

from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from starlette.requests import Request

from zenml.analytics.utils import email_opt_int
from zenml.constants import (
    ACTIVATE,
    API,
    DEACTIVATE,
    EMAIL_ANALYTICS,
    USERS,
    VERSION_1,
)
from zenml.enums import AuthScheme
from zenml.exceptions import AuthorizationException, IllegalOperationError
from zenml.logger import get_logger
from zenml.models import (
    Page,
    UserAuthModel,
    UserFilter,
    UserRequest,
    UserResponse,
    UserUpdate,
)
from zenml.zen_server.auth import (
    AuthContext,
    authenticate_credentials,
    authorize,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rate_limit import RequestLimiter
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
)
from zenml.zen_server.rbac.models import Action, Resource, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    dehydrate_response_model,
    get_allowed_resource_ids,
    get_schema_for_resource_type,
    update_resource_membership,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    server_config,
    verify_admin_status_if_no_rbac,
    zen_store,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + USERS,
    tags=["users"],
    responses={401: error_response},
)


activation_router = APIRouter(
    prefix=API + VERSION_1 + USERS,
    tags=["users"],
    responses={401: error_response},
)


current_user_router = APIRouter(
    prefix=API + VERSION_1,
    tags=["users"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[UserResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_users(
    user_filter_model: UserFilter = Depends(make_dependable(UserFilter)),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[UserResponse]:
    """Returns a list of all users.

    Args:
        user_filter_model: Model that takes care of filtering, sorting and
            pagination.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: Authentication context.

    Returns:
        A list of all users.
    """
    allowed_ids = get_allowed_resource_ids(resource_type=ResourceType.USER)
    if allowed_ids is not None:
        # Make sure users can see themselves
        allowed_ids.add(auth_context.user.id)
    else:
        if not auth_context.user.is_admin and not server_config().rbac_enabled:
            allowed_ids = {auth_context.user.id}

    user_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id, id=allowed_ids
    )

    page = zen_store().list_users(
        user_filter_model=user_filter_model, hydrate=hydrate
    )
    return dehydrate_page(page)


# When the auth scheme is set to EXTERNAL, users cannot be created via the
# API.
if server_config().auth_scheme != AuthScheme.EXTERNAL:

    @router.post(
        "",
        response_model=UserResponse,
        responses={
            401: error_response,
            409: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def create_user(
        user: UserRequest,
        auth_context: AuthContext = Security(authorize),
    ) -> UserResponse:
        """Creates a user.

        # noqa: DAR401

        Args:
            user: User to create.
            auth_context: Authentication context.

        Returns:
            The created user.
        """
        # Two ways of creating a new user:
        # 1. Create a new user with a password and have it immediately active
        # 2. Create a new user without a password and have it activated at a
        # later time with an activation token

        token: Optional[str] = None
        if user.password is None:
            user.active = False
            token = user.generate_activation_token()
        else:
            user.active = True

        verify_admin_status_if_no_rbac(
            auth_context.user.is_admin, "create user"
        )

        new_user = verify_permissions_and_create_entity(
            request_model=user,
            resource_type=ResourceType.USER,
            create_method=zen_store().create_user,
        )

        # add back the original unhashed activation token, if generated, to
        # send it back to the client
        if token:
            new_user.get_body().activation_token = token
        return new_user


@router.get(
    "/{user_name_or_id}",
    response_model=UserResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_user(
    user_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> UserResponse:
    """Returns a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: Authentication context.

    Returns:
        A specific user.
    """
    user = zen_store().get_user(
        user_name_or_id=user_name_or_id, hydrate=hydrate
    )
    if user.id != auth_context.user.id:
        verify_admin_status_if_no_rbac(
            auth_context.user.is_admin, "get other user"
        )
        verify_permission_for_model(
            user,
            action=Action.READ,
        )

    return dehydrate_response_model(user)


# When the auth scheme is set to EXTERNAL, users cannot be updated via the
# API.
if server_config().auth_scheme != AuthScheme.EXTERNAL:
    pass_change_limiter = RequestLimiter(
        day_limit=server_config().login_rate_limit_day,
        minute_limit=server_config().login_rate_limit_minute,
    )

    @router.put(
        "/{user_name_or_id}",
        response_model=UserResponse,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def update_user(
        user_name_or_id: Union[str, UUID],
        user_update: UserUpdate,
        request: Request,
        auth_context: AuthContext = Security(authorize),
    ) -> UserResponse:
        """Updates a specific user.

        Args:
            user_name_or_id: Name or ID of the user.
            user_update: the user to use for the update.
            request: The request object.
            auth_context: Authentication context.

        Returns:
            The updated user.

        Raises:
            IllegalOperationError: if the user tries change admin status,
                while not an admin, if the user tries to change the password
                of another user, or if the user tries to change their own
                password without providing the old password or providing
                an incorrect old password.
        """
        user = zen_store().get_user(user_name_or_id)

        # Use a separate object to compute the update that will be applied to
        # the user to avoid giving the API requester direct control over the
        # user attributes that are updated.
        #
        # Exclude attributes that cannot be updated through this endpoint:
        #
        # - activation_token
        # - external_user_id
        # - old_password
        #
        # Exclude things that are not always safe to update and need to be
        # validated first:
        #
        # - admin
        # - active
        # - password
        # - email_opted_in + email
        # - hub_token
        #
        safe_user_update = user_update.create_copy(
            exclude={
                "activation_token",
                "external_user_id",
                "is_admin",
                "active",
                "password",
                "old_password",
                "email_opted_in",
                "email",
                "hub_token",
            },
        )

        if user.id != auth_context.user.id:
            verify_admin_status_if_no_rbac(
                auth_context.user.is_admin, "update other user account"
            )
            verify_permission_for_model(
                user,
                action=Action.UPDATE,
            )

        # Validate a password change
        if user_update.password is not None:
            if user.id != auth_context.user.id:
                raise IllegalOperationError(
                    "Users cannot change the password of other users. Use the "
                    "account deactivation and activation flow instead."
                )

            # If the user is updating their own password, we need to verify
            # the old password
            if user_update.old_password is None:
                raise IllegalOperationError(
                    "The current password must be supplied when changing the "
                    "password."
                )

            with pass_change_limiter.limit_failed_requests(request):
                auth_user = zen_store().get_auth_user(user_name_or_id)
                if not UserAuthModel.verify_password(
                    user_update.old_password, auth_user
                ):
                    raise IllegalOperationError(
                        "The current password is incorrect."
                    )

            # Accept the password update
            safe_user_update.password = user_update.password

        # Validate an admin status change
        if (
            user_update.is_admin is not None
            and user.is_admin != user_update.is_admin
        ):
            if user.id == auth_context.user.id:
                raise IllegalOperationError(
                    "Cannot change the admin status of your own user account."
                )

            if (
                user.id != auth_context.user.id
                and not auth_context.user.is_admin
            ):
                raise IllegalOperationError(
                    "Only admins are allowed to change the admin status of "
                    "other user accounts."
                )

            # Accept the admin status update
            safe_user_update.is_admin = user_update.is_admin

        # Validate an active status change
        if (
            user_update.active is not None
            and user.active != user_update.active
        ):
            if user.id == auth_context.user.id:
                raise IllegalOperationError(
                    "Cannot change the active status of your own user account."
                )

            if (
                user.id != auth_context.user.id
                and not auth_context.user.is_admin
            ):
                raise IllegalOperationError(
                    "Only admins are allowed to change the active status of "
                    "other user accounts."
                )

            # Accept the admin status update
            safe_user_update.is_admin = user_update.is_admin

        # Validate changes to private user account information
        if (
            user_update.email_opted_in is not None
            or user_update.email is not None
            or user_update.hub_token is not None
        ):
            if user.id != auth_context.user.id:
                raise IllegalOperationError(
                    "Cannot change the private user account information for "
                    "another user account."
                )

            # Accept the private user account information update
            if safe_user_update.email_opted_in is not None:
                safe_user_update.email_opted_in = user_update.email_opted_in
                safe_user_update.email = user_update.email
            if safe_user_update.hub_token is not None:
                safe_user_update.hub_token = user_update.hub_token

        updated_user = zen_store().update_user(
            user_id=user.id,
            user_update=safe_user_update,
        )
        return dehydrate_response_model(updated_user)

    @activation_router.put(
        "/{user_name_or_id}" + ACTIVATE,
        response_model=UserResponse,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def activate_user(
        user_name_or_id: Union[str, UUID],
        user_update: UserUpdate,
    ) -> UserResponse:
        """Activates a specific user.

        Args:
            user_name_or_id: Name or ID of the user.
            user_update: the user to use for the update.

        Returns:
            The updated user.
        """
        user = zen_store().get_user(user_name_or_id)

        # Use a separate object to compute the update that will be applied to
        # the user to avoid giving the API requester direct control over the
        # user attributes that are updated.
        #
        # Exclude attributes that cannot be updated through this endpoint:
        #
        # - activation_token
        # - external_user_id
        # - is_admin
        # - active
        # - old_password
        # - hub_token
        #
        safe_user_update = user_update.create_copy(
            exclude={
                "activation_token",
                "external_user_id",
                "is_admin",
                "active",
                "old_password",
                "hub_token",
            },
        )

        # NOTE: if the activation token is not set, this will raise an
        # exception
        authenticate_credentials(
            user_name_or_id=user_name_or_id,
            activation_token=user_update.activation_token,
        )

        # Activate the user: set active to True and clear the activation token
        safe_user_update.active = True
        safe_user_update.activation_token = None
        return zen_store().update_user(
            user_id=user.id, user_update=safe_user_update
        )

    @router.put(
        "/{user_name_or_id}" + DEACTIVATE,
        response_model=UserResponse,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def deactivate_user(
        user_name_or_id: Union[str, UUID],
        auth_context: AuthContext = Security(authorize),
    ) -> UserResponse:
        """Deactivates a user and generates a new activation token for it.

        Args:
            user_name_or_id: Name or ID of the user.
            auth_context: Authentication context.

        Returns:
            The generated activation token.

        Raises:
            IllegalOperationError: if the user is trying to deactivate
                themselves.
        """
        user = zen_store().get_user(user_name_or_id)
        if user.id == auth_context.user.id:
            raise IllegalOperationError("Cannot deactivate yourself.")
        verify_admin_status_if_no_rbac(
            auth_context.user.is_admin, "deactivate user"
        )
        verify_permission_for_model(
            user,
            action=Action.UPDATE,
        )

        user_update = UserUpdate(
            active=False,
        )
        token = user_update.generate_activation_token()
        user = zen_store().update_user(
            user_id=user.id, user_update=user_update
        )
        # add back the original unhashed activation token
        user.get_body().activation_token = token
        return dehydrate_response_model(user)

    @router.delete(
        "/{user_name_or_id}",
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def delete_user(
        user_name_or_id: Union[str, UUID],
        auth_context: AuthContext = Security(authorize),
    ) -> None:
        """Deletes a specific user.

        Args:
            user_name_or_id: Name or ID of the user.
            auth_context: The authentication context.

        Raises:
            IllegalOperationError: If the user is not authorized to delete the user.
        """
        user = zen_store().get_user(user_name_or_id)

        if auth_context.user.id == user.id:
            raise IllegalOperationError(
                "You cannot delete the user account currently used to authenticate "
                "to the ZenML server. If you wish to delete this account, "
                "please authenticate with another account or contact your ZenML "
                "administrator."
            )
        else:
            verify_admin_status_if_no_rbac(
                auth_context.user.is_admin, "delete user"
            )
            verify_permission_for_model(
                user,
                action=Action.DELETE,
            )

        zen_store().delete_user(user_name_or_id=user_name_or_id)

    @router.put(
        "/{user_name_or_id}" + EMAIL_ANALYTICS,
        response_model=UserResponse,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def email_opt_in_response(
        user_name_or_id: Union[str, UUID],
        user_response: UserUpdate,
        auth_context: AuthContext = Security(authorize),
    ) -> UserResponse:
        """Sets the response of the user to the email prompt.

        Args:
            user_name_or_id: Name or ID of the user.
            user_response: User Response to email prompt
            auth_context: The authentication context of the user

        Returns:
            The updated user.

        Raises:
            AuthorizationException: if the user does not have the required
                permissions
        """
        user = zen_store().get_user(user_name_or_id)

        if str(auth_context.user.id) == str(user_name_or_id):
            user_update = UserUpdate(
                email=user_response.email,
                email_opted_in=user_response.email_opted_in,
            )

            if user_response.email_opted_in is not None:
                email_opt_int(
                    opted_in=user_response.email_opted_in,
                    email=user_response.email,
                    source="zenml server",
                )
            updated_user = zen_store().update_user(
                user_id=user.id, user_update=user_update
            )
            return dehydrate_response_model(updated_user)
        else:
            raise AuthorizationException(
                "Users can not opt in on behalf of another user."
            )


@current_user_router.get(
    "/current-user",
    response_model=UserResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_current_user(
    auth_context: AuthContext = Security(authorize),
) -> UserResponse:
    """Returns the model of the authenticated user.

    Args:
        auth_context: The authentication context.

    Returns:
        The model of the authenticated user.
    """
    return dehydrate_response_model(auth_context.user)


# When the auth scheme is set to EXTERNAL, users cannot be managed via the
# API.
if server_config().auth_scheme != AuthScheme.EXTERNAL:

    @current_user_router.put(
        "/current-user",
        response_model=UserResponse,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def update_myself(
        user: UserUpdate,
        request: Request,
        auth_context: AuthContext = Security(authorize),
    ) -> UserResponse:
        """Updates a specific user.

        Args:
            user: the user to use for the update.
            request: The request object.
            auth_context: The authentication context.

        Returns:
            The updated user.

        Raises:
            IllegalOperationError: if the current password is not supplied when
                changing the password or if the current password is incorrect.
        """
        # Use a separate object to compute the update that will be applied to
        # the user to avoid giving the API requester direct control over the
        # user attributes that are updated.
        #
        # Exclude attributes that cannot be updated through this endpoint:
        #
        # - activation_token
        # - external_user_id
        # - admin
        # - is_active
        # - old_password
        #
        safe_user_update = user.create_copy(
            exclude={
                "activation_token",
                "external_user_id",
                "is_admin",
                "active",
                "old_password",
            },
        )

        # Validate a password change
        if user.password is not None:
            # If the user is updating their password, we need to verify
            # the old password
            if user.old_password is None:
                raise IllegalOperationError(
                    "The current password must be supplied when changing the "
                    "password."
                )
            with pass_change_limiter.limit_failed_requests(request):
                auth_user = zen_store().get_auth_user(auth_context.user.id)
                if not UserAuthModel.verify_password(
                    user.old_password, auth_user
                ):
                    raise IllegalOperationError(
                        "The current password is incorrect."
                    )

            # Accept the password update
            safe_user_update.password = user.password

        updated_user = zen_store().update_user(
            user_id=auth_context.user.id, user_update=safe_user_update
        )
        return dehydrate_response_model(updated_user)


if server_config().rbac_enabled:

    @router.post(
        "/{user_name_or_id}/resource_membership",
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def update_user_resource_membership(
        user_name_or_id: Union[str, UUID],
        resource_type: str,
        resource_id: UUID,
        actions: List[str],
        auth_context: AuthContext = Security(authorize),
    ) -> None:
        """Updates resource memberships of a user.

        Args:
            user_name_or_id: Name or ID of the user.
            resource_type: Type of the resource for which to update the
                membership.
            resource_id: ID of the resource for which to update the membership.
            actions: List of actions that the user should be able to perform on
                the resource. If the user currently has permissions to perform
                actions which are not passed in this list, the permissions will
                be removed.
            auth_context: Authentication context.

        Raises:
            ValueError: If a user tries to update their own membership.
            KeyError: If no resource with the given type and ID exists.
        """
        user = zen_store().get_user(user_name_or_id)
        verify_permission_for_model(user, action=Action.READ)

        if user.id == auth_context.user.id:
            raise ValueError(
                "Not allowed to call endpoint with the authenticated user."
            )

        resource_type = ResourceType(resource_type)
        resource = Resource(type=resource_type, id=resource_id)

        schema_class = get_schema_for_resource_type(resource_type)
        model = zen_store().get_entity_by_id(
            entity_id=resource_id, schema_class=schema_class
        )

        if not model:
            raise KeyError(
                f"Resource of type {resource_type} with ID {resource_id} does "
                "not exist."
            )

        verify_permission_for_model(model=model, action=Action.SHARE)
        for action in actions:
            # Make sure users aren't able to share permissions they don't have
            # themselves
            verify_permission_for_model(model=model, action=Action(action))

        update_resource_membership(
            user=user,
            resource=resource,
            actions=[Action(action) for action in actions],
        )
