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
"""Util functions for the ZenML Server."""

import inspect
import os
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar, cast

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_SERVER,
    ENV_ZENML_SERVER_ROOT_URL_PATH,
)
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


ROOT_URL_PATH = os.getenv(ENV_ZENML_SERVER_ROOT_URL_PATH, "")


_zen_store: Optional[BaseZenStore] = None


def zen_store() -> BaseZenStore:
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


def initialize_zen_store() -> None:
    """Initialize the ZenML Store.

    Raises:
        ValueError: If the ZenML Store is using a REST back-end.
    """
    global _zen_store

    logger.debug("Initializing ZenML Store for FastAPI...")
    _zen_store = GlobalConfiguration().zen_store

    # We override track_analytics=False because we do not
    # want to track anything server side.
    _zen_store.track_analytics = False

    # Use an environment variable to flag the instance as a server
    os.environ[ENV_ZENML_SERVER] = "true"

    if _zen_store.type == StoreType.REST:
        raise ValueError(
            "Server cannot be started with a REST store type. Make sure you "
            "configure ZenML to use a non-networked store backend "
            "when trying to start the ZenML Server."
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
        try:
            inspect.signature(init_cls_and_handle_errors).bind(*args, **kwargs)
            return cls(*args, **kwargs)
        except ValidationError as e:
            for error in e.errors():
                error["loc"] = tuple(["query"] + list(error["loc"]))
            raise HTTPException(422, detail=e.errors())

    init_cls_and_handle_errors.__signature__ = inspect.signature(cls)  # type: ignore[attr-defined]

    return init_cls_and_handle_errors
