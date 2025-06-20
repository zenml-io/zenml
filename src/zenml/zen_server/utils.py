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

import asyncio
import inspect
import logging
import os
import sys
import threading
import time
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

import psutil
from pydantic import BaseModel, ValidationError
from typing_extensions import ParamSpec

from zenml import __version__ as zenml_version
from zenml.config.global_config import GlobalConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    API,
    ENV_ZENML_SERVER,
    HEALTH,
    INFO,
    READY,
    VERSION_1,
)
from zenml.exceptions import IllegalOperationError, OAuthError
from zenml.logger import get_logger
from zenml.models.v2.base.scoped import ProjectScopedFilter
from zenml.plugins.plugin_flavor_registry import PluginFlavorRegistry
from zenml.zen_server.cache import MemoryCache
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.feature_gate.feature_gate_interface import (
    FeatureGateInterface,
)
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.request_management import RequestContext, RequestManager
from zenml.zen_server.template_execution.workload_manager_interface import (
    WorkloadManagerInterface,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

if TYPE_CHECKING:
    from fastapi import Request

    from zenml.zen_server.auth import AuthContext
    from zenml.zen_server.template_execution.utils import (
        BoundedThreadPoolExecutor,
    )


P = ParamSpec("P")
R = TypeVar("R")


logger = get_logger(__name__)

_zen_store: Optional["SqlZenStore"] = None
_rbac: Optional[RBACInterface] = None
_feature_gate: Optional[FeatureGateInterface] = None
_workload_manager: Optional[WorkloadManagerInterface] = None
_run_template_executor: Optional["BoundedThreadPoolExecutor"] = None
_plugin_flavor_registry: Optional[PluginFlavorRegistry] = None
_memcache: Optional[MemoryCache] = None
_request_manager: Optional[RequestManager] = None


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


def run_template_executor() -> "BoundedThreadPoolExecutor":
    """Return the initialized run template executor.

    Raises:
        RuntimeError: If the run template executor is not initialized.

    Returns:
        The run template executor.
    """
    global _run_template_executor
    if _run_template_executor is None:
        raise RuntimeError("Run template executor not initialized")

    return _run_template_executor


def initialize_run_template_executor() -> None:
    """Initialize the run template executor."""
    global _run_template_executor
    from zenml.zen_server.template_execution.utils import (
        BoundedThreadPoolExecutor,
    )

    _run_template_executor = BoundedThreadPoolExecutor(
        max_workers=server_config().max_concurrent_template_runs,
        thread_name_prefix="zenml-run-template-executor",
    )


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


def request_manager() -> RequestManager:
    """Return the request manager.

    Returns:
        The request manager.

    Raises:
        RuntimeError: If the request manager is not initialized.
    """
    global _request_manager
    if _request_manager is None:
        raise RuntimeError("Request manager not initialized")
    return _request_manager


async def initialize_request_manager() -> None:
    """Initialize the request manager."""
    global _request_manager
    _request_manager = RequestManager(
        deduplicate=server_config().request_deduplication,
        transaction_ttl=server_config().request_cache_timeout,
        request_timeout=server_config().request_timeout,
    )
    await _request_manager.startup()


async def cleanup_request_manager() -> None:
    """Cleanup the request manager."""
    global _request_manager
    if _request_manager is not None:
        await _request_manager.shutdown()
        _request_manager = None


@overload
def async_fastapi_endpoint_wrapper(
    func: Callable[P, R],
) -> Callable[P, Awaitable[Any]]: ...


@overload
def async_fastapi_endpoint_wrapper(
    *, deduplicate: Optional[bool] = None
) -> Callable[[Callable[P, R]], Callable[P, Awaitable[Any]]]: ...


def async_fastapi_endpoint_wrapper(
    func: Optional[Callable[P, R]] = None,
    *,
    deduplicate: Optional[bool] = None,
) -> Union[
    Callable[P, Awaitable[Any]],
    Callable[[Callable[P, R]], Callable[P, Awaitable[Any]]],
]:
    """Decorator for FastAPI endpoints.

    This decorator for FastAPI endpoints does the following:
    - Converts exceptions to HTTPExceptions with the correct status code.
    - Uses the request manager to deduplicate requests and to convert the sync
    endpoint function to a coroutine.
    - Optionally enables idempotency for the endpoint.

    Args:
        func: Function to decorate.
        deduplicate: Whether to enable or disable request deduplication for
            this endpoint. If not specified, by default, the deduplication is
            enabled for POST requests and disabled for other requests.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, Awaitable[Any]]:
        @wraps(func)
        async def async_decorated(*args: P.args, **kwargs: P.kwargs) -> Any:
            @wraps(func)
            def decorated(*args: P.args, **kwargs: P.kwargs) -> Any:
                # These imports can't happen at module level as this module is also
                # used by the CLI when installed without the `server` extra
                from fastapi import HTTPException
                from fastapi.responses import JSONResponse

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

            return await request_manager().execute(
                decorated,
                deduplicate,
                *args,
                **kwargs,
            )

        return async_decorated

    if func is None:
        return decorator
    return decorator(func)


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
        "/ready",
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


def is_same_or_subdomain(source_domain: str, target_domain: str) -> bool:
    """Check if the source domain is the same or a subdomain of the target domain.

    Examples:
        is_same_or_subdomain("example.com", "example.com") -> True
        is_same_or_subdomain("alpha.example.com", "example.com") -> True
        is_same_or_subdomain("alpha.example.com", ".example.com") -> True
        is_same_or_subdomain("example.com", "alpha.example.com") -> False
        is_same_or_subdomain("alpha.beta.example.com", "beta.example.com") -> True
        is_same_or_subdomain("alpha.beta.example.com", "alpha.example.com") -> False
        is_same_or_subdomain("alphabeta.gamma.example", "beta.gamma.example") -> False

    Args:
        source_domain: The source domain to check.
        target_domain: The target domain to compare against.

    Returns:
        True if the source domain is the same or a subdomain of the target
        domain, False otherwise.
    """
    import tldextract

    # Extract the registered domain and suffix for both
    src_parts = tldextract.extract(source_domain)
    tgt_parts = tldextract.extract(target_domain)

    if src_parts == tgt_parts:
        return True  # Same domain

    # Reconstruct the base domains (e.g., example.com)
    src_base_domain = f"{src_parts.domain}.{src_parts.suffix}"
    tgt_base_domain = f"{tgt_parts.domain}.{tgt_parts.suffix}"

    if src_base_domain != tgt_base_domain:
        return False  # Different base domains

    if tgt_parts.subdomain == "":
        return True  # Subdomain

    if src_parts.subdomain.endswith(f".{tgt_parts.subdomain.lstrip('.')}"):
        return True  # Subdomain of subdomain

    return False


def get_zenml_headers() -> Dict[str, str]:
    """Get the ZenML specific headers to be included in requests made by the server.

    Returns:
        The ZenML specific headers.
    """
    config = server_config()
    headers = {
        "zenml-server-id": str(config.get_external_server_id()),
        "zenml-server-version": zenml_version,
    }
    if config.server_url:
        headers["zenml-server-url"] = config.server_url

    return headers


def set_filter_project_scope(
    filter_model: ProjectScopedFilter,
    project_name_or_id: Optional[Union[UUID, str]] = None,
) -> None:
    """Set the project scope of the filter model.

    Args:
        filter_model: The filter model to set the scope for.
        project_name_or_id: The project to set the scope for. If not
            provided, the project scope is determined from the request
            project filter or the default project, in that order.
    """
    zen_store().set_filter_project_id(
        filter_model=filter_model,
        project_name_or_id=project_name_or_id,
    )


process = psutil.Process()
fd_limit: Union[int, str] = "N/A"
if sys.platform != "win32":
    import resource

    try:
        fd_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    except Exception:
        pass


def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics.

    Returns:
        Dict containing system metrics
    """
    # Get active requests count
    from zenml.zen_server.middleware import active_requests_count

    # Memory limits
    memory = process.memory_info()

    # File descriptors
    open_fds: Union[int, str] = "N/A"
    try:
        open_fds = process.num_fds() if hasattr(process, "num_fds") else "N/A"
    except Exception:
        pass

    # Current thread name/ID
    current_thread = threading.current_thread()
    current_thread_name = current_thread.name
    current_thread_id = current_thread.ident

    return {
        "memory_used_mb": memory.rss / (1024 * 1024),
        "open_fds": open_fds,
        "fd_limit": fd_limit,
        "active_requests": active_requests_count,
        "thread_count": threading.active_count(),
        "max_worker_threads": server_config().thread_pool_size,
        "current_thread_name": current_thread_name,
        "current_thread_id": current_thread_id,
    }


def get_system_metrics_log_str(request: Optional["Request"] = None) -> str:
    """Get the system metrics as a string for logging.

    Args:
        request: The request object.

    Returns:
        The system metrics as a string for debugging logging.
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return ""
    if request and request.url.path in [HEALTH, READY]:
        # Don't log system metrics for health and ready endpoints to keep them
        # fast
        return ""
    metrics = get_system_metrics()
    return (
        " [ "
        + " ".join([f"{key}: {value}" for key, value in metrics.items()])
        + " ]"
    )


event_loop_lag_monitor_task: Optional[asyncio.Task[None]] = None


def start_event_loop_lag_monitor(threshold_ms: int = 50) -> None:
    """Start the event loop lag monitor.

    Args:
        threshold_ms: The threshold in milliseconds for the event loop lag.
    """
    global event_loop_lag_monitor_task

    async def monitor() -> None:
        while True:
            start = time.perf_counter()
            await asyncio.sleep(0)
            delay = (time.perf_counter() - start) * 1000
            if delay > threshold_ms:
                logger.warning(
                    f"⚠️  Event loop lag detected: {delay:.2f}ms"
                    "If you see this message, it means that the ZenML server is "
                    "under heavy load and the clients might start experiencing "
                    "connection reset errors. Please consider scaling up the "
                    "server."
                )
            await asyncio.sleep(0.5)

    event_loop_lag_monitor_task = asyncio.create_task(monitor())


def stop_event_loop_lag_monitor() -> None:
    """Stop the event loop lag monitor."""
    global event_loop_lag_monitor_task
    if event_loop_lag_monitor_task:
        event_loop_lag_monitor_task.cancel()
        event_loop_lag_monitor_task = None


def get_auth_context() -> Optional["AuthContext"]:
    """Get the authentication context for the current request.

    Returns:
        The authentication context.
    """
    request_context = request_manager().current_request
    return request_context.auth_context


def get_current_request_context() -> RequestContext:
    """Get the current request context.

    Returns:
        The current request context.
    """
    return request_manager().current_request
