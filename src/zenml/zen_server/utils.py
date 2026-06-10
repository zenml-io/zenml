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
from contextvars import ContextVar
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
    INFO,
    VERSION_1,
)
from zenml.exceptions import IllegalOperationError, OAuthError
from zenml.logger import get_logger
from zenml.models.v2.base.scoped import ProjectScopedFilter
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.feature_gate.feature_gate_interface import (
    FeatureGateInterface,
)
from zenml.zen_server.pipeline_execution.workload_manager_interface import (
    WorkloadManagerInterface,
)
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.request_management import RequestContext, RequestManager
from zenml.zen_server.streaming.broadcaster import StreamBroadcaster
from zenml.zen_server.streaming.brokers.base import StreamBroker
from zenml.zen_stores.resource_pools.store_interface import (
    ResourcePoolsSQLStoreInterface,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

if TYPE_CHECKING:
    from fastapi import Request

    from zenml.zen_server.auth import AuthContext
    from zenml.zen_server.pipeline_execution.utils import (
        BoundedThreadPoolExecutor,
    )
    from zenml.zen_server.streaming.run_end_handler import (
        StreamEndEventHandler,
    )


P = ParamSpec("P")
R = TypeVar("R")


logger = get_logger(__name__)

_zen_store: Optional["SqlZenStore"] = None
_rbac: Optional[RBACInterface] = None
_feature_gate: Optional[FeatureGateInterface] = None
_workload_manager: Optional[WorkloadManagerInterface] = None
_resource_pool_store: Optional[ResourcePoolsSQLStoreInterface] = None
_snapshot_executor: Optional["BoundedThreadPoolExecutor"] = None
_request_manager: Optional[RequestManager] = None
_stream_broker: Optional[StreamBroker] = None
_stream_broadcaster: Optional[StreamBroadcaster] = None
_stream_end_handler: Optional["StreamEndEventHandler"] = None
_auth_context: ContextVar[Optional["AuthContext"]] = ContextVar(
    "auth_context", default=None
)


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


def stream_broker() -> StreamBroker:
    """Return the initialized stream broker.

    Returns:
        The active stream broker.

    Raises:
        RuntimeError: If streaming is disabled.
    """
    global _stream_broker
    if _stream_broker is None:
        raise RuntimeError(
            "Stream broker not initialized; streaming is disabled. "
            "Set `stream_broker_implementation_source` on the server config."
        )
    return _stream_broker


def stream_broadcaster() -> StreamBroadcaster:
    """Return the initialized stream broadcaster.

    Returns:
        The active stream broadcaster.

    Raises:
        RuntimeError: If streaming is disabled.
    """
    global _stream_broadcaster
    if _stream_broadcaster is None:
        raise RuntimeError(
            "Stream broadcaster not initialized. Streaming is disabled. "
            "Set `stream_broker_implementation_source` on the server config."
        )
    return _stream_broadcaster


async def initialize_streaming() -> None:
    """Initialize the live event streaming components.

    Raises:
        RuntimeError: If the configured broker class can't be loaded or
            its connectivity probe fails.
    """
    global _stream_broker, _stream_broadcaster, _stream_end_handler

    cfg = server_config()
    source = cfg.stream_broker_implementation_source
    if not source:
        return

    from zenml.utils import source_utils

    try:
        broker_class: Type[StreamBroker] = (
            source_utils.load_and_validate_class(
                source=source, expected_class=StreamBroker
            )
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not load stream broker class {source}: {exc}. "
            "Check `stream_broker_implementation_source` on the server "
            "config."
        ) from exc

    try:
        _stream_broker = broker_class()
    except Exception as exc:
        _stream_broker = None
        raise RuntimeError(
            f"Could not instantiate stream broker {source}: {exc}"
        ) from exc

    from zenml.zen_server.streaming.brokers.utils import startup_probe_key

    try:
        await _stream_broker.latest_id(startup_probe_key())
    except Exception as exc:
        broker = _stream_broker
        _stream_broker = None
        try:
            await broker.close()
        except Exception:
            logger.debug("Probe-failure broker close errored", exc_info=True)
        raise RuntimeError(
            f"Stream broker {source} startup probe failed: {exc}"
        ) from exc

    _stream_broadcaster = StreamBroadcaster(
        broker=_stream_broker,
        max_subscribers_per_stream=cfg.streaming_max_subscribers_per_stream,
        idle_grace_seconds=cfg.streaming_broadcaster_idle_grace_seconds,
    )

    from zenml.dispatcher import EventDispatcher
    from zenml.zen_server.streaming.run_end_handler import (
        StreamEndEventHandler,
    )

    _stream_end_handler = StreamEndEventHandler(
        broker=_stream_broker, loop=asyncio.get_running_loop()
    )
    EventDispatcher().register_event_handler(_stream_end_handler)


async def shutdown_streaming() -> None:
    """Cancel broadcaster readers, unregister handlers, close the broker."""
    global _stream_broker, _stream_broadcaster, _stream_end_handler
    if _stream_end_handler is not None:
        from zenml.dispatcher import EventDispatcher

        try:
            EventDispatcher().unregister_event_handler(_stream_end_handler)
        except Exception:
            logger.exception("Error unregistering stream-end handler")
        _stream_end_handler = None
    if _stream_broadcaster is not None:
        try:
            await _stream_broadcaster.shutdown()
        except Exception:
            logger.exception("Error during stream broadcaster shutdown")
        _stream_broadcaster = None
    if _stream_broker is not None:
        try:
            await _stream_broker.close()
        except Exception:
            logger.exception("Error during stream broker close")
        _stream_broker = None


def resource_pool_store() -> ResourcePoolsSQLStoreInterface:
    """Return the initialized resource pool store component.

    Raises:
        RuntimeError: If the resource pool store component is not initialized.

    Returns:
        The resource pool store component.
    """
    global _resource_pool_store
    if _resource_pool_store is None:
        raise RuntimeError("Resource pool store component not initialized")
    return _resource_pool_store


def initialize_resource_pool_store() -> None:
    """Initialize the resource pool store component.

    This does not fail if the source can't be loaded but only logs a warning.
    """
    global _resource_pool_store

    if source := server_config().resource_pool_implementation_source:
        from zenml.utils import source_utils

        try:
            resource_pool_store_class: Type[ResourcePoolsSQLStoreInterface] = (
                source_utils.load_and_validate_class(
                    source=source,
                    expected_class=ResourcePoolsSQLStoreInterface,
                )
            )
        except (ModuleNotFoundError, KeyError):
            logger.warning("Unable to load resource pool store source.")
        else:
            _resource_pool_store = resource_pool_store_class(store=zen_store())


def snapshot_executor() -> "BoundedThreadPoolExecutor":
    """Return the initialized snapshot executor.

    Raises:
        RuntimeError: If the snapshot executor is not initialized.

    Returns:
        The snapshot executor.
    """
    global _snapshot_executor
    if _snapshot_executor is None:
        raise RuntimeError("Snapshot executor not initialized")

    return _snapshot_executor


def initialize_snapshot_executor() -> None:
    """Initialize the snapshot executor."""
    global _snapshot_executor
    from zenml.zen_server.pipeline_execution.utils import (
        BoundedThreadPoolExecutor,
    )

    _snapshot_executor = BoundedThreadPoolExecutor(
        max_workers=server_config().max_concurrent_snapshot_runs,
        thread_name_prefix="zenml-snapshot-executor",
    )


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

    _request_manager = RequestManager()
    await _request_manager.startup()


async def cleanup_request_manager() -> None:
    """Cleanup the request manager."""
    global _request_manager
    if _request_manager is not None:
        await _request_manager.shutdown()
        _request_manager = None


def handle_endpoint_errors(
    func: Callable[P, R],
) -> Callable[P, R]:
    """Translate raised exceptions into FastAPI HTTP responses.

    OAuthError becomes a JSONResponse (it needs to carry its own body
    schema); HTTPException is re-raised unchanged; anything else is
    funneled through `http_exception_from_error` so the status code
    follows the REST_API_EXCEPTIONS mapping. Use this on async endpoints
    that don't go through `async_fastapi_endpoint_wrapper` (e.g. SSE).

    Args:
        func: The endpoint function to wrap.

    Returns:
        The wrapped function.
    """

    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        # Imports kept inside the wrapper: this module is also imported by
        # the CLI which doesn't ship with the `server` extra.
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        try:
            return func(*args, **kwargs)
        except OAuthError as error:
            return JSONResponse(  # type: ignore[return-value]
                status_code=error.status_code,
                content=error.to_dict(),
            )
        except HTTPException:
            raise
        except Exception as error:
            logger.exception("API error")
            raise http_exception_from_error(error)

    return wrapped


def async_handle_endpoint_errors(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Async variant of `handle_endpoint_errors`.

    Args:
        func: The async endpoint function to wrap.

    Returns:
        The wrapped async function.
    """

    @wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        try:
            return await func(*args, **kwargs)
        except OAuthError as error:
            return JSONResponse(  # type: ignore[return-value]
                status_code=error.status_code,
                content=error.to_dict(),
            )
        except HTTPException:
            raise
        except Exception as error:
            logger.exception("API error")
            raise http_exception_from_error(error)

    return wrapped


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
        translated = handle_endpoint_errors(func)

        @wraps(func)
        async def async_decorated(*args: P.args, **kwargs: P.kwargs) -> Any:
            return await request_manager().execute(
                translated,
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
    single_input_params = getattr(cls, "API_SINGLE_INPUT_PARAMS", [])

    for qp in params.keys():
        if qp not in single_input_params:
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


def get_request_path(request: "Request") -> str:
    """Return the routed request path, immune to Host-header poisoning.

    Security checks must not use ``request.url.path``. Starlette rebuilds
    ``request.url`` from the (unvalidated) ``Host`` header, so a crafted Host
    header can make ``request.url.path`` differ from the path the router
    actually dispatched to (CVE-2026-48710 / GHSA-86qp-5c8j-p5mr). The raw ASGI
    ``scope["path"]`` is the value routing uses and the Host header cannot
    influence it, so it is the only safe basis for a path-based decision.

    Args:
        request: The incoming request.

    Returns:
        The raw ASGI path that routing dispatched to.
    """
    return str(request.scope["path"])


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
    path = get_request_path(request)
    # Check if this is not an excluded endpoint
    if path in [user_prefix + suffix for suffix in excluded_user_apis]:
        return False

    # Check if this is other user request
    if path.startswith(user_prefix):
        return True

    # Exclude system paths
    if any(path.startswith(system_path) for system_path in system_paths):
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


def get_system_metrics(
    logger: Optional[logging.Logger] = None,
    log_level: int = logging.DEBUG,
) -> Dict[str, Any]:
    """Get comprehensive system metrics for enabled log records.

    Metrics are only collected when the provided logger, or this module's
    logger when omitted, is enabled for ``log_level``. This keeps debug-only
    structured fields cheap when debug logging is disabled.

    Args:
        logger: Logger whose logging level decides whether metrics are
            collected.
        log_level: Logging level that must be enabled to collect metrics.
            Defaults to ``logging.DEBUG``.

    Returns:
        Dict containing system metrics, or an empty dict if ``log_level`` is
        not enabled.
    """
    active_logger = logger or get_logger(__name__)
    if not active_logger.isEnabledFor(log_level):
        return {}

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


def set_auth_context(auth_context: "AuthContext") -> None:
    """Set the authentication context for the current request.

    Args:
        auth_context: The authentication context.
    """
    _auth_context.set(auth_context)


def get_auth_context() -> Optional["AuthContext"]:
    """Get the authentication context for the current request.

    Returns:
        The authentication context.
    """
    if auth_context := _auth_context.get():
        return auth_context
    request_context = request_manager().current_request
    return request_context.auth_context


def get_current_request_context() -> RequestContext:
    """Get the current request context.

    Returns:
        The current request context.
    """
    return request_manager().current_request


async def register_event_handlers() -> None:
    """Register event handlers to the event dispatcher."""
    from zenml.dispatcher import EventDispatcher, EventHandler

    if server_config().event_handler_sources:
        from zenml.utils import source_utils

        for source in server_config().event_handler_sources:
            logger.info("Registering event handler %s", source)

            try:
                event_handler_cls: type[EventHandler] = (
                    source_utils.load_and_validate_class(
                        source=source,
                        expected_class=EventHandler,
                    )
                )
            except Exception as exc:
                logger.exception(
                    f"Failed to load event handler {source}", exc_info=exc
                )
                continue
            else:
                try:
                    event_handler = await event_handler_cls.create()
                    EventDispatcher().register_event_handler(event_handler)
                except Exception as exc:
                    logger.exception(
                        f"Failed to register event handler {source}",
                        exc_info=exc,
                    )
