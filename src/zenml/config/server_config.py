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
"""Functionality to support ZenML GlobalConfiguration."""

import json
import os
from secrets import token_hex
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from zenml.constants import (
    DEFAULT_ZENML_JWT_TOKEN_ALGORITHM,
    DEFAULT_ZENML_JWT_TOKEN_LEEWAY,
    DEFAULT_ZENML_SERVER_DEVICE_AUTH_POLLING,
    DEFAULT_ZENML_SERVER_DEVICE_AUTH_TIMEOUT,
    DEFAULT_ZENML_SERVER_GENERIC_API_TOKEN_LIFETIME,
    DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_DAY,
    DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_MINUTE,
    DEFAULT_ZENML_SERVER_MAX_DEVICE_AUTH_ATTEMPTS,
    DEFAULT_ZENML_SERVER_MAX_REQUEST_BODY_SIZE_IN_BYTES,
    DEFAULT_ZENML_SERVER_NAME,
    DEFAULT_ZENML_SERVER_PIPELINE_RUN_AUTH_WINDOW,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_CACHE,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_CONTENT,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_CSP,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_HSTS,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_PERMISSIONS,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_REFERRER,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_XFO,
    DEFAULT_ZENML_SERVER_SECURE_HEADERS_XXP,
    DEFAULT_ZENML_SERVER_THREAD_POOL_SIZE,
    ENV_ZENML_SERVER_PREFIX,
)
from zenml.enums import AuthScheme
from zenml.logger import get_logger
from zenml.models import ServerDeploymentType
from zenml.utils.pydantic_utils import before_validator_handler

logger = get_logger(__name__)


def generate_jwt_secret_key() -> str:
    """Generate a random JWT secret key.

    This key is used to sign and verify generated JWT tokens.

    Returns:
        A random JWT secret key.
    """
    return token_hex(32)


class ServerConfiguration(BaseModel):
    """ZenML Server configuration attributes.

    All these attributes can be set through the environment with the `ZENML_SERVER_`-Prefix.
    The value of the `ZENML_SERVER_DEPLOYMENT_TYPE` environment variable will be extracted to deployment_type.

    Attributes:
        deployment_type: The type of ZenML server deployment that is running.
        server_url: The URL where the ZenML server API is reachable. Must be
            configured for features that involve triggering workloads from the
            ZenML dashboard (e.g., running pipelines). If not specified, the
            clients will use the same URL used to connect them to the ZenML
            server.
        dashboard_url: The URL where the ZenML dashboard is reachable.
            If not specified, the `server_url` value is used. This should be
            configured if the dashboard is served from a different URL than the
            ZenML server.
        root_url_path: The root URL path for the ZenML API and dashboard.
        auth_scheme: The authentication scheme used by the ZenML server.
        jwt_token_algorithm: The algorithm used to sign and verify JWT tokens.
        jwt_token_issuer: The issuer of the JWT tokens. If not specified, the
            issuer is set to the ZenML Server ID.
        jwt_token_audience: The audience of the JWT tokens. If not specified,
            the audience is set to the ZenML Server ID.
        jwt_token_leeway_seconds: The leeway in seconds allowed when verifying
            the expiration time of JWT tokens.
        jwt_token_expire_minutes: The expiration time of JWT tokens in minutes.
            If not specified, generated JWT tokens will not be set to expire.
        jwt_secret_key: The secret key used to sign and verify JWT tokens. If
            not specified, a random secret key is generated.
        auth_cookie_name: The name of the http-only cookie used to store the JWT
            token. If not specified, the cookie name is set to a value computed
            from the ZenML server ID.
        auth_cookie_domain: The domain of the http-only cookie used to store the
            JWT token. If not specified, the cookie will be valid for the
            domain where the ZenML server is running.
        cors_allow_origins: The origins allowed to make cross-origin requests
            to the ZenML server. If not specified, all origins are allowed.
        max_failed_device_auth_attempts: The maximum number of failed OAuth 2.0
            device authentication attempts before the device is locked.
        device_auth_timeout: The timeout in seconds after which a pending OAuth
            2.0 device authorization request expires.
        device_auth_polling_interval: The polling interval in seconds used to
            poll the OAuth 2.0 device authorization endpoint.
        device_expiration_minutes: The time in minutes that an OAuth 2.0 device is
            allowed to be used to authenticate with the ZenML server. If not
            set or if `jwt_token_expire_minutes` is not set, the devices are
            allowed to be used indefinitely. This controls the expiration time
            of the JWT tokens issued to clients after they have authenticated
            with the ZenML server using an OAuth 2.0 device.
        trusted_device_expiration_minutes: The time in minutes that a trusted OAuth 2.0
            device is allowed to be used to authenticate with the ZenML server.
            If not set or if `jwt_token_expire_minutes` is not set, the devices
            are allowed to be used indefinitely. This controls the expiration
            time of the JWT tokens issued to clients after they have
            authenticated with the ZenML server using an OAuth 2.0 device
            that has been marked as trusted.
        generic_api_token_lifetime: The lifetime in seconds that generic
            short-lived API tokens issued for automation purposes are valid.
        external_login_url: The login URL of an external authenticator service
            to use with the `EXTERNAL` authentication scheme.
        external_user_info_url: The user info URL of an external authenticator
            service to use with the `EXTERNAL` authentication scheme.
        external_cookie_name: The name of the http-only cookie used to store the
            bearer token used to authenticate with the external authenticator
            service. Must be specified if the `EXTERNAL` authentication scheme
            is used.
        external_server_id: The ID of the ZenML server to use with the
            `EXTERNAL` authentication scheme. If not specified, the regular
            ZenML server ID is used.
        metadata: Additional metadata to be associated with the ZenML server.
        rbac_implementation_source: Source pointing to a class implementing
            the RBAC interface defined by
            `zenml.zen_server.rbac_interface.RBACInterface`. If not specified,
            RBAC will not be enabled for this server.
        feature_gate_implementation_source: Source pointing to a class
            implementing the feature gate interface defined by
            `zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface`.
            If not specified, feature usage will not be gated/tracked for this
            server.
        workload_manager_implementation_source: Source pointing to a class
            implementing the workload management interface.
        pipeline_run_auth_window: The default time window in minutes for which
            a pipeline run action is allowed to authenticate with the ZenML
            server.
        login_rate_limit_minute: The number of login attempts allowed per minute.
        login_rate_limit_day: The number of login attempts allowed per day.
        secure_headers_server: Custom value to be set in the `Server` HTTP
            header to identify the server. If not specified, or if set to one of
            the reserved values `enabled`, `yes`, `true`, `on`, the `Server`
            header will be set to the default value (ZenML server ID). If set to
            one of the reserved values `disabled`, `no`, `none`, `false`, `off`
            or to an empty string, the `Server` header will not be included in
            responses.
        secure_headers_hsts: The server header value to be set in the HTTP
            header `Strict-Transport-Security`. If not specified, or if set to
            one of the reserved values `enabled`, `yes`, `true`, `on`, the
            `Strict-Transport-Security` header will be set to the default value
            (`max-age=63072000; includeSubdomains`). If set to one of
            the reserved values `disabled`, `no`, `none`, `false`, `off` or to
            an empty string, the `Strict-Transport-Security` header will not be
            included in responses.
        secure_headers_xfo: The server header value to be set in the HTTP
            header `X-Frame-Options`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `X-Frame-Options`
            header will be set to the default value (`SAMEORIGIN`). If set to
            one of the reserved values `disabled`, `no`, `none`, `false`, `off`
            or to an empty string, the `X-Frame-Options` header will not be
            included in responses.
        secure_headers_xxp: The server header value to be set in the HTTP
            header `X-XSS-Protection`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `X-XSS-Protection`
            header will be set to the default value (`0`). If set to one of the
            reserved values `disabled`, `no`, `none`, `false`, `off` or
            to an empty string, the `X-XSS-Protection` header will not be
            included in responses. NOTE: this header is deprecated and should
            always be set to `0`. The `Content-Security-Policy` header should be
            used instead.
        secure_headers_content: The server header value to be set in the HTTP
            header `X-Content-Type-Options`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `X-Content-Type-Options` header will be set to the default value
            (`nosniff`). If set to one of the reserved values `disabled`, `no`,
            `none`, `false`, `off` or to an empty string, the
            `X-Content-Type-Options` header will not be included in responses.
        secure_headers_csp: The server header value to be set in the HTTP
            header `Content-Security-Policy`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `Content-Security-Policy` header will be set to a default value
            that is compatible with the ZenML dashboard. If set to one of the
            reserved values `disabled`, `no`, `none`, `false`, `off` or to an
            empty string, the `Content-Security-Policy` header will not be
            included in responses.
        secure_headers_referrer: The server header value to be set in the HTTP
            header `Referrer-Policy`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `Referrer-Policy`
            header will be set to the default value
            (`no-referrer-when-downgrade`). If set to one of the reserved values
            `disabled`, `no`, `none`, `false`, `off` or to an empty string, the
            `Referrer-Policy` header will not be included in responses.
        secure_headers_cache: The server header value to be set in the HTTP
            header `Cache-Control`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `Cache-Control`
            header will be set to the default value
            (`no-store, no-cache, must-revalidate`). If set to one of the
            reserved values `disabled`, `no`, `none`, `false`, `off` or to an
            empty string, the `Cache-Control` header will not be included in
            responses.
        secure_headers_permissions: The server header value to be set in the
            HTTP header `Permissions-Policy`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `Permissions-Policy` header will be set to the default value
            (`accelerometer=(), camera=(), geolocation=(), gyroscope=(),
            magnetometer=(), microphone=(), payment=(), usb=()`). If set to
            one of the reserved values `disabled`, `no`, `none`, `false`, `off`
            or to an empty string, the `Permissions-Policy` header will not be
            included in responses.
        server_name: The name of the ZenML server. Used only during initial
            deployment. Can be changed later as a part of the server settings.
        display_announcements: Whether to display announcements about ZenML in
            the dashboard. Used only during initial deployment. Can be changed
            later as a part of the server settings.
        display_updates: Whether to display notifications about ZenML updates in
            the dashboard. Used only during initial deployment. Can be changed
            later as a part of the server settings.
        auto_activate: Whether to automatically activate the server and create a
            default admin user account with an empty password during the initial
            deployment.
        max_request_body_size_in_bytes: The maximum size of the request body in
            bytes. If not specified, the default value of 256 Kb will be used.
        memcache_max_capacity: The maximum number of entries that the memory
            cache can hold. If not specified, the default value of 1000 will be
            used.
        memcache_default_expiry: The default expiry time in seconds for cache
            entries. If not specified, the default value of 30 seconds will be
            used.
    """

    deployment_type: ServerDeploymentType = ServerDeploymentType.OTHER
    server_url: Optional[str] = None
    dashboard_url: Optional[str] = None
    root_url_path: str = ""
    metadata: Dict[str, Any] = {}
    auth_scheme: AuthScheme = AuthScheme.OAUTH2_PASSWORD_BEARER
    jwt_token_algorithm: str = DEFAULT_ZENML_JWT_TOKEN_ALGORITHM
    jwt_token_issuer: Optional[str] = None
    jwt_token_audience: Optional[str] = None
    jwt_token_leeway_seconds: int = DEFAULT_ZENML_JWT_TOKEN_LEEWAY
    jwt_token_expire_minutes: Optional[int] = None
    jwt_secret_key: str = Field(default_factory=generate_jwt_secret_key)
    auth_cookie_name: Optional[str] = None
    auth_cookie_domain: Optional[str] = None
    cors_allow_origins: Optional[List[str]] = None
    max_failed_device_auth_attempts: int = (
        DEFAULT_ZENML_SERVER_MAX_DEVICE_AUTH_ATTEMPTS
    )
    device_auth_timeout: int = DEFAULT_ZENML_SERVER_DEVICE_AUTH_TIMEOUT
    device_auth_polling_interval: int = (
        DEFAULT_ZENML_SERVER_DEVICE_AUTH_POLLING
    )
    device_expiration_minutes: Optional[int] = None
    trusted_device_expiration_minutes: Optional[int] = None

    generic_api_token_lifetime: PositiveInt = (
        DEFAULT_ZENML_SERVER_GENERIC_API_TOKEN_LIFETIME
    )

    external_login_url: Optional[str] = None
    external_user_info_url: Optional[str] = None
    external_cookie_name: Optional[str] = None
    external_server_id: Optional[UUID] = None

    rbac_implementation_source: Optional[str] = None
    feature_gate_implementation_source: Optional[str] = None
    workload_manager_implementation_source: Optional[str] = None
    pipeline_run_auth_window: int = (
        DEFAULT_ZENML_SERVER_PIPELINE_RUN_AUTH_WINDOW
    )

    rate_limit_enabled: bool = False
    login_rate_limit_minute: int = DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_MINUTE
    login_rate_limit_day: int = DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_DAY

    secure_headers_server: Union[bool, str] = Field(
        default=True,
        union_mode="left_to_right",
    )
    secure_headers_hsts: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_HSTS,
        union_mode="left_to_right",
    )
    secure_headers_xfo: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_XFO,
        union_mode="left_to_right",
    )
    secure_headers_xxp: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_XXP,
        union_mode="left_to_right",
    )
    secure_headers_content: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_CONTENT,
        union_mode="left_to_right",
    )
    secure_headers_csp: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_CSP,
        union_mode="left_to_right",
    )
    secure_headers_referrer: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_REFERRER,
        union_mode="left_to_right",
    )
    secure_headers_cache: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_CACHE,
        union_mode="left_to_right",
    )
    secure_headers_permissions: Union[bool, str] = Field(
        default=DEFAULT_ZENML_SERVER_SECURE_HEADERS_PERMISSIONS,
        union_mode="left_to_right",
    )

    server_name: str = DEFAULT_ZENML_SERVER_NAME
    display_announcements: bool = True
    display_updates: bool = True
    auto_activate: bool = False

    thread_pool_size: int = DEFAULT_ZENML_SERVER_THREAD_POOL_SIZE

    max_request_body_size_in_bytes: int = (
        DEFAULT_ZENML_SERVER_MAX_REQUEST_BODY_SIZE_IN_BYTES
    )

    memcache_max_capacity: int = 1000
    memcache_default_expiry: int = 30

    _deployment_id: Optional[UUID] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _validate_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the server configuration.

        Args:
            data: The server configuration values.

        Returns:
            The validated server configuration values.

        Raises:
            ValueError: If the server configuration is invalid.
        """
        if data.get("auth_scheme") == AuthScheme.EXTERNAL:
            # If the authentication scheme is set to `EXTERNAL`, the
            # external authenticator URLs must be specified.
            if not data.get("external_login_url") or not data.get(
                "external_user_info_url"
            ):
                raise ValueError(
                    "The external login and user info authenticator "
                    "URLs must be specified when using the EXTERNAL "
                    "authentication scheme."
                )

            # If the authentication scheme is set to `EXTERNAL`, the
            # external cookie name must be specified.
            if not data.get("external_cookie_name"):
                raise ValueError(
                    "The external cookie name must be specified when "
                    "using the EXTERNAL authentication scheme."
                )

        if cors_allow_origins := data.get("cors_allow_origins"):
            origins = cors_allow_origins.split(",")
            data["cors_allow_origins"] = origins
        else:
            data["cors_allow_origins"] = ["*"]

        # if metadata is a string, convert it to a dictionary
        if isinstance(data.get("metadata"), str):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"The server metadata is not a valid JSON string: {e}"
                )

        # if one of the secure headers options is set to a boolean value, set
        # the corresponding value
        for k, v in data.copy().items():
            if k.startswith("secure_headers_") and isinstance(v, str):
                if v.lower() in ["disabled", "no", "none", "false", "off", ""]:
                    data[k] = False
                if v.lower() in ["enabled", "yes", "true", "on"]:
                    # Revert to the default value if the header is enabled
                    del data[k]

        # Handle merging of user-defined secure_headers_csp value with the default value
        if "secure_headers_csp" in data:
            user_defined_csp = data["secure_headers_csp"]
            if isinstance(user_defined_csp, str):
                # Parse the user-defined CSP string into a dictionary
                user_defined_csp_dict = {}
                for directive in user_defined_csp.split(";"):
                    directive = directive.strip()
                    if directive:
                        key, value = directive.split(" ", 1)
                        user_defined_csp_dict[key] = value.strip("'\"")

                # Merge the user-defined CSP dictionary with the default CSP dictionary
                default_csp_dict = {}
                for directive in DEFAULT_ZENML_SERVER_SECURE_HEADERS_CSP.split(
                    ";"
                ):
                    directive = directive.strip()
                    if directive:
                        key, value = directive.split(" ", 1)
                        default_csp_dict[key] = value.strip("'\"")

                merged_csp_dict = {**default_csp_dict, **user_defined_csp_dict}

                # Convert the merged CSP dictionary back to a string
                merged_csp_str = "; ".join(
                    f"{key} {value}" for key, value in merged_csp_dict.items()
                )
                data["secure_headers_csp"] = merged_csp_str

        return data

    @property
    def deployment_id(self) -> UUID:
        """Get the ZenML server deployment ID.

        Returns:
            The ZenML server deployment ID.
        """
        from zenml.config.global_config import GlobalConfiguration

        if self._deployment_id:
            return self._deployment_id

        self._deployment_id = (
            GlobalConfiguration().zen_store.get_deployment_id()
        )

        return self._deployment_id

    @property
    def rbac_enabled(self) -> bool:
        """Whether RBAC is enabled on the server or not.

        Returns:
            Whether RBAC is enabled on the server or not.
        """
        return self.rbac_implementation_source is not None

    @property
    def feature_gate_enabled(self) -> bool:
        """Whether feature gating is enabled on the server or not.

        Returns:
            Whether feature gating is enabled on the server or not.
        """
        return self.feature_gate_implementation_source is not None

    @property
    def workload_manager_enabled(self) -> bool:
        """Whether workload management is enabled on the server or not.

        Returns:
            Whether workload management is enabled on the server or not.
        """
        return self.workload_manager_implementation_source is not None

    def get_jwt_token_issuer(self) -> str:
        """Get the JWT token issuer.

        If not configured, the issuer is set to the ZenML Server ID.

        Returns:
            The JWT token issuer.
        """
        if self.jwt_token_issuer:
            return self.jwt_token_issuer

        self.jwt_token_issuer = str(self.deployment_id)

        return self.jwt_token_issuer

    def get_jwt_token_audience(self) -> str:
        """Get the JWT token audience.

        If not configured, the audience is set to the ZenML Server ID.

        Returns:
            The JWT token audience.
        """
        if self.jwt_token_audience:
            return self.jwt_token_audience

        self.jwt_token_audience = str(self.deployment_id)

        return self.jwt_token_audience

    def get_auth_cookie_name(self) -> str:
        """Get the authentication cookie name.

        If not configured, the cookie name is set to a value computed from the
        ZenML server ID.

        Returns:
            The authentication cookie name.
        """
        if self.auth_cookie_name:
            return self.auth_cookie_name

        self.auth_cookie_name = f"zenml-server-{self.deployment_id}"

        return self.auth_cookie_name

    def get_external_server_id(self) -> UUID:
        """Get the external server ID.

        If not configured, the regular ZenML server ID is used.

        Returns:
            The external server ID.
        """
        if self.external_server_id:
            return self.external_server_id

        self.external_server_id = self.deployment_id

        return self.external_server_id

    @classmethod
    def get_server_config(cls) -> "ServerConfiguration":
        """Get the server configuration.

        Returns:
            The server configuration.
        """
        env_server_config: Dict[str, Any] = {}
        for k, v in os.environ.items():
            if v == "":
                continue
            if k.startswith(ENV_ZENML_SERVER_PREFIX):
                env_server_config[
                    k[len(ENV_ZENML_SERVER_PREFIX) :].lower()
                ] = v

        return ServerConfiguration(**env_server_config)

    model_config = ConfigDict(
        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra="allow",
    )
