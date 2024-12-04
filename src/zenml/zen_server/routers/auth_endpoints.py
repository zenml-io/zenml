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
"""Endpoint definitions for authentication (login)."""

from typing import Optional, Union
from urllib.parse import urlencode
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Security,
    status,
)
from fastapi.param_functions import Form
from starlette.requests import Request

from zenml.constants import (
    API,
    API_TOKEN,
    DEVICE_AUTHORIZATION,
    DEVICE_VERIFY,
    DEVICES,
    LOGIN,
    LOGOUT,
    VERSION_1,
)
from zenml.enums import (
    APITokenType,
    AuthScheme,
    ExecutionStatus,
    OAuthDeviceStatus,
    OAuthGrantTypes,
)
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    OAuthDeviceAuthorizationResponse,
    OAuthDeviceInternalRequest,
    OAuthDeviceInternalUpdate,
    OAuthDeviceUserAgentHeader,
    OAuthRedirectResponse,
    OAuthTokenResponse,
)
from zenml.zen_server.auth import (
    AuthContext,
    authenticate_api_key,
    authenticate_credentials,
    authenticate_device,
    authenticate_external_user,
    authorize,
    generate_access_token,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rate_limit import rate_limit_requests
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.utils import (
    get_ip_location,
    handle_exceptions,
    server_config,
    zen_store,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["auth"],
    responses={401: error_response},
)


class OAuthLoginRequestForm:
    """OAuth2 grant type request form.

    This form allows multiple grant types to be used with the same endpoint:
    * standard OAuth2 password grant type
    * standard  OAuth2 device authorization grant type
    * ZenML service account + API key grant type (proprietary)
    * ZenML External Authenticator grant type (proprietary)
    """

    def __init__(
        self,
        grant_type: Optional[str] = Form(None),
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        device_code: Optional[str] = Form(None),
    ):
        """Initializes the form.

        Args:
            grant_type: The grant type.
            username: The username. Only used for the password grant type.
            password: The password. Only used for the password grant type.
            client_id: The client ID.
            device_code: The device code. Only used for the device authorization
                grant type.

        Raises:
            HTTPException: If the request is invalid.
        """
        config = server_config()

        if not grant_type:
            # Detect the grant type from the form data
            if username is not None:
                self.grant_type = OAuthGrantTypes.OAUTH_PASSWORD
            elif password:
                self.grant_type = OAuthGrantTypes.ZENML_API_KEY
            elif device_code:
                self.grant_type = OAuthGrantTypes.OAUTH_DEVICE_CODE
            elif config.auth_scheme == AuthScheme.EXTERNAL:
                self.grant_type = OAuthGrantTypes.ZENML_EXTERNAL
            elif config.auth_scheme in [
                AuthScheme.OAUTH2_PASSWORD_BEARER,
                AuthScheme.NO_AUTH,
                AuthScheme.HTTP_BASIC,
            ]:
                # For no auth and basic HTTP auth schemes, we also allow the
                # password grant type to be used for backwards compatibility
                self.grant_type = OAuthGrantTypes.OAUTH_PASSWORD
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request: grant type is required.",
                )
        else:
            if grant_type not in OAuthGrantTypes.values():
                logger.info(
                    f"Request with unsupported grant type: {grant_type}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant type: {grant_type}",
                )
            self.grant_type = OAuthGrantTypes(grant_type)

        if self.grant_type == OAuthGrantTypes.OAUTH_PASSWORD:
            # For the no auth and basic HTTP auth schemes, we also allow the
            # password grant type to be used for compatibility with other
            # auth schemes
            if config.auth_scheme not in [
                AuthScheme.OAUTH2_PASSWORD_BEARER,
                AuthScheme.NO_AUTH,
                AuthScheme.HTTP_BASIC,
            ]:
                logger.info(
                    f"Request with unsupported grant type: {self.grant_type}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant type: {self.grant_type}.",
                )
            if not username:
                logger.info("Request with missing username")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request: username is required.",
                )
            self.username = username
            self.password = password or ""
        elif self.grant_type == OAuthGrantTypes.OAUTH_DEVICE_CODE:
            if not device_code or not client_id:
                logger.info("Request with missing device code or client ID")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request: device code and client ID are "
                    "required.",
                )
            try:
                self.client_id = UUID(client_id)
            except ValueError:
                logger.info(f"Request with invalid client ID: {client_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request: invalid client ID.",
                )
            self.device_code = device_code
        elif self.grant_type == OAuthGrantTypes.ZENML_API_KEY:
            if not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key is required.",
                )
            self.api_key = password
        elif self.grant_type == OAuthGrantTypes.ZENML_EXTERNAL:
            if config.auth_scheme != AuthScheme.EXTERNAL:
                logger.info(
                    f"Request with unsupported grant type: {self.grant_type}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant type: {self.grant_type}.",
                )


@router.post(
    LOGIN,
    response_model=Union[OAuthTokenResponse, OAuthRedirectResponse],
)
@rate_limit_requests(
    day_limit=server_config().login_rate_limit_day,
    minute_limit=server_config().login_rate_limit_minute,
)
@handle_exceptions
def token(
    request: Request,
    response: Response,
    auth_form_data: OAuthLoginRequestForm = Depends(),
) -> Union[OAuthTokenResponse, OAuthRedirectResponse]:
    """OAuth2 token endpoint.

    Args:
        request: The request object.
        response: The response object.
        auth_form_data: The OAuth 2.0 authentication form data.

    Returns:
        An access token or a redirect response.

    Raises:
        ValueError: If the grant type is invalid.
    """
    config = server_config()
    if auth_form_data.grant_type == OAuthGrantTypes.OAUTH_PASSWORD:
        auth_context = authenticate_credentials(
            user_name_or_id=auth_form_data.username,
            password=auth_form_data.password,
        )

    elif auth_form_data.grant_type == OAuthGrantTypes.OAUTH_DEVICE_CODE:
        auth_context = authenticate_device(
            client_id=auth_form_data.client_id,
            device_code=auth_form_data.device_code,
        )
    elif auth_form_data.grant_type == OAuthGrantTypes.ZENML_API_KEY:
        auth_context = authenticate_api_key(
            api_key=auth_form_data.api_key,
        )

    elif auth_form_data.grant_type == OAuthGrantTypes.ZENML_EXTERNAL:
        assert config.external_cookie_name is not None
        assert config.external_login_url is not None

        authorization_url = config.external_login_url

        # First, try to get the external access token from the external cookie
        external_access_token = request.cookies.get(
            config.external_cookie_name
        )
        if not external_access_token:
            # Next, try to get the external access token from the authorization
            # header
            authorization_header = request.headers.get("Authorization")
            if authorization_header:
                scheme, _, token = authorization_header.partition(" ")
                if token and scheme.lower() == "bearer":
                    external_access_token = token
                    logger.info(
                        "External access token found in authorization header."
                    )
        else:
            logger.info("External access token found in cookie.")

        if not external_access_token:
            logger.info(
                "External access token not found. Redirecting to "
                "external authenticator."
            )

            # Redirect the user to the external authentication login endpoint
            return OAuthRedirectResponse(authorization_url=authorization_url)

        auth_context = authenticate_external_user(
            external_access_token=external_access_token
        )

    else:
        # Shouldn't happen, because we verify all grants in the form data
        raise ValueError("Invalid grant type.")

    return generate_access_token(
        user_id=auth_context.user.id,
        response=response,
        device=auth_context.device,
        api_key=auth_context.api_key,
    )


@router.get(
    LOGOUT,
)
def logout(
    response: Response,
) -> None:
    """Logs out the user.

    Args:
        response: The response object.
    """
    config = server_config()

    # Remove the HTTP only cookie even if it does not exist
    response.delete_cookie(
        key=config.get_auth_cookie_name(),
        httponly=True,
        samesite="lax",
        domain=config.auth_cookie_domain,
    )


@router.post(
    DEVICE_AUTHORIZATION,
    response_model=OAuthDeviceAuthorizationResponse,
)
def device_authorization(
    request: Request,
    client_id: UUID = Form(...),
) -> OAuthDeviceAuthorizationResponse:
    """OAuth2 device authorization endpoint.

    This endpoint implements the OAuth2 device authorization grant flow as
    defined in https://tools.ietf.org/html/rfc8628. It is called to initiate
    the device authorization flow by requesting a device and user code for a
    given client ID.

    For a new client ID, a new OAuth device is created, stored in the DB and
    returned to the client along with a pair of newly generated device and user
    codes. If a device for the given client ID already exists, the existing
    DB entry is reused and new device and user codes are generated.

    Args:
        request: The request object.
        client_id: The client ID.

    Returns:
        The device authorization response.
    """
    config = server_config()
    store = zen_store()

    try:
        # Use this opportunity to delete expired devices
        store.delete_expired_authorized_devices()
    except Exception:
        logger.exception("Failed to delete expired devices")

    # Fetch additional details about the client from the user-agent header
    user_agent_header = request.headers.get("User-Agent")
    if user_agent_header:
        device_details = OAuthDeviceUserAgentHeader.decode(user_agent_header)
    else:
        device_details = OAuthDeviceUserAgentHeader()

    # Fetch the IP address of the client
    ip_address: str = ""
    city, region, country = "", "", ""
    forwarded = request.headers.get("X-Forwarded-For")

    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        ip_address = request.client.host

    if ip_address:
        city, region, country = get_ip_location(ip_address)

    # Check if a device is already registered for the same client ID.
    try:
        device_model = store.get_internal_authorized_device(
            client_id=client_id
        )
    except KeyError:
        device_model = store.create_authorized_device(
            OAuthDeviceInternalRequest(
                client_id=client_id,
                expires_in=config.device_auth_timeout,
                ip_address=ip_address,
                city=city,
                region=region,
                country=country,
                **device_details.model_dump(exclude_none=True),
            )
        )
    else:
        # Put the device into pending state and generate new codes. This
        # effectively invalidates the old codes and the device cannot be used
        # for authentication anymore.
        device_model = store.update_internal_authorized_device(
            device_id=device_model.id,
            update=OAuthDeviceInternalUpdate(
                trusted_device=False,
                expires_in=config.device_auth_timeout,
                status=OAuthDeviceStatus.PENDING,
                failed_auth_attempts=0,
                generate_new_codes=True,
                ip_address=ip_address,
                city=city,
                region=region,
                country=country,
                **device_details.model_dump(exclude_none=True),
            ),
        )

    dashboard_url = config.dashboard_url or config.server_url

    if dashboard_url:
        verification_uri = dashboard_url.lstrip("/") + DEVICES + DEVICE_VERIFY
    else:
        verification_uri = DEVICES + DEVICE_VERIFY

    verification_uri_complete = (
        verification_uri
        + "?"
        + urlencode(
            dict(
                device_id=str(device_model.id),
                user_code=str(device_model.user_code),
            )
        )
    )
    return OAuthDeviceAuthorizationResponse(
        device_code=device_model.device_code,
        user_code=device_model.user_code,
        expires_in=config.device_auth_timeout,
        interval=config.device_auth_polling_interval,
        verification_uri=verification_uri,
        verification_uri_complete=verification_uri_complete,
    )


@router.get(
    API_TOKEN,
    response_model=str,
)
@handle_exceptions
def api_token(
    token_type: APITokenType = APITokenType.GENERIC,
    expires_in: Optional[int] = None,
    schedule_id: Optional[UUID] = None,
    pipeline_run_id: Optional[UUID] = None,
    step_run_id: Optional[UUID] = None,
    auth_context: AuthContext = Security(authorize),
) -> str:
    """Generate an API token for the current user.

    Use this endpoint to generate an API token for the current user. Two types
    of API tokens are supported:

    * Generic API token: This token is short-lived and can be used for
    generic automation tasks. The expiration can be set by the user, but the
    server will impose a maximum expiration time.
    * Workload API token: This token is scoped to a specific pipeline run, step
    run or schedule and is used by pipeline workloads to authenticate with the
    server. A pipeline run ID, step run ID or schedule ID must be provided and
    the generated token will only be valid for the indicated pipeline run, step
    run or schedule. No time limit is imposed on the validity of the token.
    A workload API token can be used to authenticate and generate another
    workload API token, but only for the same schedule, pipeline run ID or step
    run ID, in that order.

    Args:
        token_type: The type of API token to generate.
        expires_in: The expiration time of the generic API token in seconds.
            If not set, the server will use the default expiration time for
            generic API tokens. The server also imposes a maximum expiration
            time.
        schedule_id: The ID of the schedule to scope the workload API token to.
        pipeline_run_id: The ID of the pipeline run to scope the workload API
            token to.
        step_run_id: The ID of the step run to scope the workload API token to.
        auth_context: The authentication context.

    Returns:
        The API token.

    Raises:
        AuthorizationException: If not authorized to generate the API token.
        ValueError: If the request is invalid.
    """
    token = auth_context.access_token
    if not token or not auth_context.encoded_access_token:
        # Should not happen
        raise AuthorizationException("Not authenticated.")

    if token_type == APITokenType.GENERIC:
        if schedule_id or pipeline_run_id or step_run_id:
            raise ValueError(
                "Generic API tokens cannot be scoped to a schedule, pipeline "
                "run or step run."
            )

        config = server_config()

        if not expires_in:
            expires_in = config.generic_api_token_lifetime

        if expires_in > config.generic_api_token_max_lifetime:
            raise ValueError(
                f"The maximum expiration time for generic API tokens allowed "
                f"by this server is {config.generic_api_token_max_lifetime} "
                "seconds."
            )

        return generate_access_token(
            user_id=token.user_id,
            expires_in=expires_in,
        ).access_token

    verify_permission(
        resource_type=ResourceType.PIPELINE_RUN, action=Action.CREATE
    )

    schedule_id = schedule_id or token.schedule_id
    pipeline_run_id = pipeline_run_id or token.pipeline_run_id
    step_run_id = step_run_id or token.step_run_id

    if not pipeline_run_id and not schedule_id and not step_run_id:
        raise ValueError(
            "Workload API tokens must be scoped to a schedule, pipeline run "
            "or step run."
        )

    if schedule_id and token.schedule_id and schedule_id != token.schedule_id:
        raise AuthorizationException(
            f"Unable to scope API token to schedule {schedule_id}. The "
            f"token used to authorize this request is already scoped to "
            f"schedule {token.schedule_id}."
        )

    if (
        pipeline_run_id
        and token.pipeline_run_id
        and pipeline_run_id != token.pipeline_run_id
    ):
        raise AuthorizationException(
            f"Unable to scope API token to pipeline run {pipeline_run_id}. The "
            f"token used to authorize this request is already scoped to "
            f"pipeline run {token.pipeline_run_id}."
        )

    if step_run_id and token.step_run_id and step_run_id != token.step_run_id:
        raise AuthorizationException(
            f"Unable to scope API token to step run {step_run_id}. The "
            f"token used to authorize this request is already scoped to "
            f"step run {token.step_run_id}."
        )

    if schedule_id:
        # The schedule must exist
        try:
            schedule = zen_store().get_schedule(schedule_id, hydrate=False)
        except KeyError:
            raise ValueError(
                f"Schedule {schedule_id} does not exist and API tokens cannot "
                "be generated for non-existent schedules for security reasons."
            )

        if not schedule.active:
            raise ValueError(
                f"Schedule {schedule_id} is not active and API tokens cannot "
                "be generated for inactive schedules for security reasons."
            )

    if pipeline_run_id:
        # The pipeline run must exist and the run must not be concluded
        try:
            pipeline_run = zen_store().get_run(pipeline_run_id, hydrate=False)
        except KeyError:
            raise ValueError(
                f"Pipeline run {pipeline_run_id} does not exist and API tokens "
                "cannot be generated for non-existent pipeline runs for "
                "security reasons."
            )

        if pipeline_run.status in [
            ExecutionStatus.FAILED,
            ExecutionStatus.COMPLETED,
        ]:
            raise ValueError(
                f"The execution of pipeline run {pipeline_run_id} has already "
                "concluded and API tokens can no longer be generated for it "
                "for security reasons."
            )

    if step_run_id:
        # The step run must exist and the step must not be concluded
        try:
            step_run = zen_store().get_run_step(step_run_id, hydrate=False)
        except KeyError:
            raise ValueError(
                f"Step run {step_run_id} does not exist and API tokens cannot "
                "be generated for non-existent step runs for security reasons."
            )

        if step_run.status in [
            ExecutionStatus.FAILED,
            ExecutionStatus.COMPLETED,
        ]:
            raise ValueError(
                f"The execution of step run {step_run_id} has already "
                "concluded and API tokens can no longer be generated for it "
                "for security reasons."
            )

    return generate_access_token(
        user_id=token.user_id,
        # Keep the original API key and device token scopes
        api_key=auth_context.api_key,
        device=auth_context.device,
        schedule_id=schedule_id,
        pipeline_run_id=pipeline_run_id,
        step_run_id=step_run_id,
        # Never expire the token
        expires_in=0,
    ).access_token
