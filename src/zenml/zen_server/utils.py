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
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, cast
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from zenml.config.global_config import GlobalConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    ENV_ZENML_SERVER,
)
from zenml.enums import ServerProviderType
from zenml.exceptions import OAuthError
from zenml.logger import get_logger
from zenml.zen_server.deploy.deployment import ServerDeployment
from zenml.zen_server.deploy.local.local_zen_server import (
    LocalServerDeploymentConfig,
)
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

_zen_store: Optional["SqlZenStore"] = None
_rbac: Optional[RBACInterface] = None


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
    if not gc.uses_default_store() and gc.store is not None:
        logger.debug("Getting URL of connected server.")
        parsed_url = urlparse(gc.store.url)
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

    Args:
        cls: The model class.

    Returns:
        Function to use in FastAPI `Depends`.
    """

    def init_cls_and_handle_errors(*args: Any, **kwargs: Any) -> BaseModel:
        from fastapi import HTTPException

        try:
            inspect.signature(init_cls_and_handle_errors).bind(*args, **kwargs)
            return cls(*args, **kwargs)
        except ValidationError as e:
            for error in e.errors():
                error["loc"] = tuple(["query"] + list(error["loc"]))
            raise HTTPException(422, detail=e.errors())

    init_cls_and_handle_errors.__signature__ = inspect.signature(cls)  # type: ignore[attr-defined]

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
