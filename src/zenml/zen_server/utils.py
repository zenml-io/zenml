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
    List,
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
    API,
    ENV_ZENML_SERVER,
    INFO,
    VERSION_1,
)
from zenml.enums import StoreType
from zenml.exceptions import IllegalOperationError, OAuthError
from zenml.logger import get_logger
from zenml.plugins.plugin_flavor_registry import PluginFlavorRegistry
from zenml.zen_server.cache import MemoryCache
from zenml.zen_server.deploy.deployment import (
    LocalServerDeployment,
)
from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.feature_gate.feature_gate_interface import (
    FeatureGateInterface,
)
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.template_execution.workload_manager_interface import (
    WorkloadManagerInterface,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

if TYPE_CHECKING:
    from fastapi import Request

logger = get_logger(__name__)

_zen_store: Optional["SqlZenStore"] = None
_rbac: Optional[RBACInterface] = None
_feature_gate: Optional[FeatureGateInterface] = None
_workload_manager: Optional[WorkloadManagerInterface] = None
_plugin_flavor_registry: Optional[PluginFlavorRegistry] = None
_memcache: Optional[MemoryCache] = None


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


def initialize_memcache(max_capacity: int, default_expiry: int) -> None:
    """Initialize the memory cache.

    Args:
        max_capacity: The maximum capacity of the cache.
        default_expiry: The default expiry time in seconds.
    """
    global _memcache
    _memcache = MemoryCache(max_capacity, default_expiry)


def memcache() -> MemoryCache:
    """Return the memory cache.

    Returns:
        The memory cache.

    Raises:
        RuntimeError: If the memory cache is not initialized.
    """
    if _memcache is None:
        raise RuntimeError("Memory cache not initialized")
    return _memcache


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


def get_local_server() -> Optional["LocalServerDeployment"]:
    """Get the active local server.

    Call this function to retrieve the local server deployed on this machine.

    Returns:
        The local server deployment or None, if no local server deployment was
        found.
    """
    from zenml.zen_server.deploy.deployer import LocalServerDeployer

    deployer = LocalServerDeployer()
    try:
        return deployer.get_server()
    except ServerDeploymentNotFoundError:
        return None


def connected_to_local_server() -> bool:
    """Check if the client is connected to a local server.

    Returns:
        True if the client is connected to a local server, False otherwise.
    """
    from zenml.zen_server.deploy.deployer import LocalServerDeployer

    deployer = LocalServerDeployer()
    return deployer.is_connected_to_server()


def show_dashboard(
    local: bool = False,
    ngrok_token: Optional[str] = None,
) -> None:
    """Show the ZenML dashboard.

    Args:
        local: Whether to show the dashboard for the local server or the
            one for the active server.
        ngrok_token: An ngrok auth token to use for exposing the ZenML
            dashboard on a public domain. Primarily used for accessing the
            dashboard in Colab.

    Raises:
        RuntimeError: If no server is connected.
    """
    from zenml.utils.dashboard_utils import show_dashboard
    from zenml.utils.networking_utils import get_or_create_ngrok_tunnel

    url: Optional[str] = None
    if not local:
        gc = GlobalConfiguration()
        if gc.store_configuration.type == StoreType.REST:
            url = gc.store_configuration.url

    if not url:
        # Else, check for local servers
        server = get_local_server()
        if server and server.status and server.status.url:
            url = server.status.url

    if not url:
        raise RuntimeError(
            "ZenML is not connected to any server right now. Please use "
            "`zenml login` to connect to a server or spin up a new local server "
            "via `zenml login --local`."
        )

    if ngrok_token:
        parsed_url = urlparse(url)

        ngrok_url = get_or_create_ngrok_tunnel(
            ngrok_token=ngrok_token, port=parsed_url.port or 80
        )
        logger.debug(f"Tunneling dashboard from {url} to {ngrok_url}.")
        url = ngrok_url

    show_dashboard(url)


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

    from zenml.zen_server.exceptions import error_detail

    def init_cls_and_handle_errors(*args: Any, **kwargs: Any) -> BaseModel:
        from fastapi import HTTPException

        try:
            inspect.signature(init_cls_and_handle_errors).bind(*args, **kwargs)
            return cls(*args, **kwargs)
        except ValidationError as e:
            detail = error_detail(e, exception_type=ValueError)
            raise HTTPException(422, detail=detail)

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


def is_user_request(request: "Request") -> bool:
    """Determine if the incoming request is a user request.

    This function checks various aspects of the request to determine
    if it's a user-initiated request or a system request.

    Args:
        request: The incoming FastAPI request object.

    Returns:
        True if it's a user request, False otherwise.
    """
    # Define system paths that should be excluded
    system_paths: List[str] = [
        "/health",
        "/metrics",
        "/system",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    user_prefix = f"{API}{VERSION_1}"
    excluded_user_apis = [INFO]
    # Check if this is not an excluded endpoint
    if request.url.path in [
        user_prefix + suffix for suffix in excluded_user_apis
    ]:
        return False

    # Check if this is other user request
    if request.url.path.startswith(user_prefix):
        return True

    # Exclude system paths
    if any(request.url.path.startswith(path) for path in system_paths):
        return False

    # Exclude requests with specific headers
    if request.headers.get("X-System-Request") == "true":
        return False

    # Exclude requests from certain user agents (e.g., monitoring tools)
    user_agent = request.headers.get("User-Agent", "").lower()
    system_agents = ["prometheus", "datadog", "newrelic", "pingdom"]
    if any(agent in user_agent for agent in system_agents):
        return False

    # Check for internal IP addresses
    client_host = request.client.host if request.client else None
    if client_host and (
        client_host.startswith("10.") or client_host.startswith("192.168.")
    ):
        return False

    # Exclude OPTIONS requests (often used for CORS preflight)
    if request.method == "OPTIONS":
        return False

    # Exclude specific query parameters that might indicate system requests
    if request.query_params.get("system_check"):
        return False

    # If none of the above conditions are met, consider it a user request
    return True
