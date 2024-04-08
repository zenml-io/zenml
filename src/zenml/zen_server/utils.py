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
"""Util functions for the ZenML Server."""

import inspect
import os
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from zenml.config.global_config import GlobalConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    ENV_ZENML_SERVER,
)
from zenml.enums import ServerProviderType
from zenml.exceptions import IllegalOperationError, OAuthError
from zenml.logger import get_logger
from zenml.plugins.plugin_flavor_registry import PluginFlavorRegistry
from zenml.zen_server.deploy.deployment import ServerDeployment
from zenml.zen_server.deploy.local.local_zen_server import (
    LocalServerDeploymentConfig,
)
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.feature_gate.feature_gate_interface import (
    FeatureGateInterface,
)
from zenml.zen_server.pipeline_deployment.workload_manager_interface import (
    WorkloadManagerInterface,
)
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_stores.sql_zen_store import SqlZenStore

if TYPE_CHECKING:
    import secure

logger = get_logger(__name__)

_zen_store: Optional["SqlZenStore"] = None
_rbac: Optional[RBACInterface] = None
_feature_gate: Optional[FeatureGateInterface] = None
_workload_manager: Optional[WorkloadManagerInterface] = None
_plugin_flavor_registry: Optional[PluginFlavorRegistry] = None
_secure_headers: Optional["secure.Secure"] = None


def zen_store() -> "SqlZenStore":
    """Initialize the ZenML Store.

    Returns:
        The ZenML Store.

    Raises:
        RuntimeError: If the ZenML Store has not been initialized.
    """
    global _zen_store
    if _zen_store is None:
        raise RuntimeError("ZenML Store not initialized")
    return _zen_store


def plugin_flavor_registry() -> PluginFlavorRegistry:
    """Get the plugin flavor registry.

    Returns:
        The plugin flavor registry.
    """
    global _plugin_flavor_registry
    if _plugin_flavor_registry is None:
        _plugin_flavor_registry = PluginFlavorRegistry()
        _plugin_flavor_registry.initialize_plugins()
    return _plugin_flavor_registry


def rbac() -> RBACInterface:
    """Return the initialized RBAC component.

    Raises:
        RuntimeError: If the RBAC component is not initialized.

    Returns:
        The RBAC component.
    """
    global _rbac
    if _rbac is None:
        raise RuntimeError("RBAC component not initialized")
    return _rbac


def initialize_rbac() -> None:
    """Initialize the RBAC component."""
    global _rbac

    if rbac_source := server_config().rbac_implementation_source:
        from zenml.utils import source_utils

        implementation_class = source_utils.load_and_validate_class(
            rbac_source, expected_class=RBACInterface
        )
        _rbac = implementation_class()


def feature_gate() -> FeatureGateInterface:
    """Return the initialized Feature Gate component.

    Raises:
        RuntimeError: If the RBAC component is not initialized.

    Returns:
        The RBAC component.
    """
    global _feature_gate
    if _feature_gate is None:
        raise RuntimeError("Feature gate component not initialized.")
    return _feature_gate


def initialize_feature_gate() -> None:
    """Initialize the Feature Gate component."""
    global _feature_gate

    if (
        feature_gate_source
        := server_config().feature_gate_implementation_source
    ):
        from zenml.utils import source_utils

        implementation_class = source_utils.load_and_validate_class(
            feature_gate_source, expected_class=FeatureGateInterface
        )
        _feature_gate = implementation_class()


def workload_manager() -> WorkloadManagerInterface:
    """Return the initialized workload manager component.

    Raises:
        RuntimeError: If the workload manager component is not initialized.

    Returns:
        The workload manager component.
    """
    global _workload_manager
    if _workload_manager is None:
        raise RuntimeError("Workload manager component not initialized")
    return _workload_manager


def initialize_workload_manager() -> None:
    """Initialize the workload manager component.

    This does not fail if the source can't be loaded but only logs a warning.
    """
    global _workload_manager

    if source := server_config().workload_manager_implementation_source:
        from zenml.utils import source_utils

        try:
            workload_manager_class: Type[WorkloadManagerInterface] = (
                source_utils.load_and_validate_class(
                    source=source, expected_class=WorkloadManagerInterface
                )
            )
        except (ModuleNotFoundError, KeyError):
            logger.warning("Unable to load workload manager source.")
        else:
            _workload_manager = workload_manager_class()


def initialize_plugins() -> None:
    """Initialize the event plugins registry."""
    plugin_flavor_registry().initialize_plugins()


def initialize_zen_store() -> None:
    """Initialize the ZenML Store.

    Raises:
        ValueError: If the ZenML Store is using a REST back-end.
    """
    logger.debug("Initializing ZenML Store for FastAPI...")

    # Use an environment variable to flag the instance as a server
    os.environ[ENV_ZENML_SERVER] = "true"

    zen_store_ = GlobalConfiguration().zen_store

    if not isinstance(zen_store_, SqlZenStore):
        raise ValueError(
            "Server cannot be started with a REST store type. Make sure you "
            "configure ZenML to use a non-networked store backend "
            "when trying to start the ZenML Server."
        )

    global _zen_store
    _zen_store = zen_store_


def secure_headers() -> "secure.Secure":
    """Return the secure headers component.

    Returns:
        The secure headers component.

    Raises:
        RuntimeError: If the secure headers component is not initialized.
    """
    global _secure_headers
    if _secure_headers is None:
        raise RuntimeError("Secure headers component not initialized")
    return _secure_headers


def initialize_secure_headers() -> None:
    """Initialize the secure headers component."""
    import secure

    global _secure_headers

    config = server_config()

    # For each of the secure headers supported by the `secure` library, we
    # check if the corresponding configuration is set in the server
    # configuration:
    #
    # - if set to `True`, we use the default value for the header
    # - if set to a string, we use the string as the value for the header
    # - if set to `False`, we don't set the header

    server: Optional[secure.Server] = None
    if config.secure_headers_server:
        server = secure.Server()
        if isinstance(config.secure_headers_server, str):
            server.set(config.secure_headers_server)
        else:
            server.set(str(config.deployment_id))

    hsts: Optional[secure.StrictTransportSecurity] = None
    if config.secure_headers_hsts:
        hsts = secure.StrictTransportSecurity()
        if isinstance(config.secure_headers_hsts, str):
            hsts.set(config.secure_headers_hsts)

    xfo: Optional[secure.XFrameOptions] = None
    if config.secure_headers_xfo:
        xfo = secure.XFrameOptions()
        if isinstance(config.secure_headers_xfo, str):
            xfo.set(config.secure_headers_xfo)

    xxp: Optional[secure.XXSSProtection] = None
    if config.secure_headers_xxp:
        xxp = secure.XXSSProtection()
        if isinstance(config.secure_headers_xxp, str):
            xxp.set(config.secure_headers_xxp)

    csp: Optional[secure.ContentSecurityPolicy] = None
    if config.secure_headers_csp:
        csp = secure.ContentSecurityPolicy()
        if isinstance(config.secure_headers_csp, str):
            csp.set(config.secure_headers_csp)

    content: Optional[secure.XContentTypeOptions] = None
    if config.secure_headers_content:
        content = secure.XContentTypeOptions()
        if isinstance(config.secure_headers_content, str):
            content.set(config.secure_headers_content)

    referrer: Optional[secure.ReferrerPolicy] = None
    if config.secure_headers_referrer:
        referrer = secure.ReferrerPolicy()
        if isinstance(config.secure_headers_referrer, str):
            referrer.set(config.secure_headers_referrer)

    cache: Optional[secure.CacheControl] = None
    if config.secure_headers_cache:
        cache = secure.CacheControl()
        if isinstance(config.secure_headers_cache, str):
            cache.set(config.secure_headers_cache)

    permissions: Optional[secure.PermissionsPolicy] = None
    if config.secure_headers_permissions:
        permissions = secure.PermissionsPolicy()
        if isinstance(config.secure_headers_permissions, str):
            permissions.value = config.secure_headers_permissions

    _secure_headers = secure.Secure(
        server=server,
        hsts=hsts,
        xfo=xfo,
        xxp=xxp,
        csp=csp,
        content=content,
        referrer=referrer,
        cache=cache,
        permissions=permissions,
    )


_server_config: Optional[ServerConfiguration] = None


def server_config() -> ServerConfiguration:
    """Returns the ZenML Server configuration.

    Returns:
        The ZenML Server configuration.
    """
    global _server_config
    if _server_config is None:
        _server_config = ServerConfiguration.get_server_config()
    return _server_config


def get_active_deployment(local: bool = False) -> Optional["ServerDeployment"]:
    """Get the active local or remote server deployment.

    Call this function to retrieve the local or remote server deployment that
    was last provisioned on this machine.

    Args:
        local: Whether to return the local active deployment or the remote one.

    Returns:
        The local or remote active server deployment or None, if no deployment
        was found.
    """
    from zenml.zen_server.deploy.deployer import ServerDeployer

    deployer = ServerDeployer()
    if local:
        servers = deployer.list_servers(provider_type=ServerProviderType.LOCAL)
        if not servers:
            servers = deployer.list_servers(
                provider_type=ServerProviderType.DOCKER
            )
    else:
        servers = deployer.list_servers()

    if not servers:
        return None

    for server in servers:
        if server.config.provider in [
            ServerProviderType.LOCAL,
            ServerProviderType.DOCKER,
        ]:
            if local:
                return server
        elif not local:
            return server

    return None


def get_active_server_details() -> Tuple[str, Optional[int]]:
    """Get the URL of the current ZenML Server.

    When multiple servers are present, the following precedence is used to
    determine which server to use:
    - If the client is connected to a server, that server has precedence.
    - If no server is connected, a server that was deployed remotely has
        precedence over a server that was deployed locally.

    Returns:
        The URL and port of the currently active server.

    Raises:
        RuntimeError: If no server is active.
    """
    # Check for connected servers first
    gc = GlobalConfiguration()
    if not gc.uses_default_store():
        logger.debug("Getting URL of connected server.")
        parsed_url = urlparse(gc.store_configuration.url)
        return f"{parsed_url.scheme}://{parsed_url.hostname}", parsed_url.port
    # Else, check for deployed servers
    server = get_active_deployment(local=False)
    if server:
        logger.debug("Getting URL of remote server.")
    else:
        server = get_active_deployment(local=True)
        logger.debug("Getting URL of local server.")

    if server and server.status and server.status.url:
        if isinstance(server.config, LocalServerDeploymentConfig):
            return server.status.url, server.config.port
        return server.status.url, None

    raise RuntimeError(
        "ZenML is not connected to any server right now. Please use "
        "`zenml connect` to connect to a server or spin up a new local server "
        "via `zenml up`."
    )


F = TypeVar("F", bound=Callable[..., Any])


def handle_exceptions(func: F) -> F:
    """Decorator to handle exceptions in the API.

    Args:
        func: Function to decorate.

    Returns:
        Decorated function.
    """

    @wraps(func)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        # These imports can't happen at module level as this module is also
        # used by the CLI when installed without the `server` extra
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        from zenml.zen_server.auth import AuthContext, set_auth_context

        for arg in args:
            if isinstance(arg, AuthContext):
                set_auth_context(arg)
                break
        else:
            for _, arg in kwargs.items():
                if isinstance(arg, AuthContext):
                    set_auth_context(arg)
                    break

        try:
            return func(*args, **kwargs)
        except OAuthError as error:
            # The OAuthError is special because it needs to have a JSON response
            return JSONResponse(
                status_code=error.status_code,
                content=error.to_dict(),
            )
        except HTTPException:
            raise
        except Exception as error:
            logger.exception("API error")
            http_exception = http_exception_from_error(error)
            raise http_exception

    return cast(F, decorated)


# Code from https://github.com/tiangolo/fastapi/issues/1474#issuecomment-1160633178
# to send 422 response when receiving invalid query parameters
def make_dependable(cls: Type[BaseModel]) -> Callable[..., Any]:
    """This function makes a pydantic model usable for fastapi query parameters.

    Additionally, it converts `InternalServerError`s that would happen due to
    `pydantic.ValidationError` into 422 responses that signal an invalid
    request.

    Check out https://github.com/tiangolo/fastapi/issues/1474 for context.

    Usage:
        def f(model: Model = Depends(make_dependable(Model))):
            ...

    UPDATE: Function from above mentioned Github issue was extended to support
    multi-input parameters, e.g. tags: List[str]. It needs a default set to Query(<default>),
    rather just plain <default>.

    Args:
        cls: The model class.

    Returns:
        Function to use in FastAPI `Depends`.
    """
    from fastapi import Query

    def init_cls_and_handle_errors(*args: Any, **kwargs: Any) -> BaseModel:
        from fastapi import HTTPException

        try:
            inspect.signature(init_cls_and_handle_errors).bind(*args, **kwargs)
            return cls(*args, **kwargs)
        except ValidationError as e:
            for error in e.errors():
                error["loc"] = tuple(["query"] + list(error["loc"]))
            raise HTTPException(422, detail=e.errors())

    params = {v.name: v for v in inspect.signature(cls).parameters.values()}
    query_params = getattr(cls, "API_MULTI_INPUT_PARAMS", [])
    for qp in query_params:
        if qp in params:
            params[qp] = inspect.Parameter(
                name=params[qp].name,
                default=Query(params[qp].default),
                kind=params[qp].kind,
                annotation=params[qp].annotation,
            )

    init_cls_and_handle_errors.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=[v for v in params.values()]
    )

    return init_cls_and_handle_errors


def get_ip_location(ip_address: str) -> Tuple[str, str, str]:
    """Get the location of the given IP address.

    Args:
        ip_address: The IP address to get the location for.

    Returns:
        A tuple of city, region, country.
    """
    import ipinfo  # type: ignore[import-untyped]

    try:
        handler = ipinfo.getHandler()
        details = handler.getDetails(ip_address)
        return (
            details.city,
            details.region,
            details.country_name,
        )
    except Exception:
        logger.exception(f"Could not get IP location for {ip_address}.")
        return "", "", ""


def verify_admin_status_if_no_rbac(
    admin_status: Optional[bool],
    action: Optional[str] = None,
) -> None:
    """Validate the admin status for sensitive requests.

    Only add this check in endpoints meant for admin use only.

    Args:
        admin_status: Whether the user is an admin or not. This is only used
            if explicitly specified in the call and even if passed will be
            ignored, if RBAC is enabled.
        action: The action that is being performed, used for output only.

    Raises:
        IllegalOperationError: If the admin status is not valid.
    """
    if not server_config().rbac_enabled:
        if not action:
            action = "this action"
        else:
            action = f"`{action.strip('`')}`"

        if admin_status is False:
            raise IllegalOperationError(
                message=f"Only admin users can perform {action} "
                "without RBAC enabled.",
            )
    return
