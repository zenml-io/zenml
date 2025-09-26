#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Validation functions for hooks."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Tuple,
    Union,
)

from pydantic import ConfigDict, PydanticSchemaGenerationError, ValidationError

from zenml.config.source import Source
from zenml.exceptions import HookValidationException
from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.pydantic_utils import validate_function_args

logger = get_logger(__name__)


if TYPE_CHECKING:
    from zenml.types import HookSpecification, InitHookSpecification


def resolve_and_validate_hook(
    hook: Union["HookSpecification", "InitHookSpecification"],
    hook_kwargs: Optional[Dict[str, Any]] = None,
    allow_exception_arg: bool = False,
) -> Tuple[Source, Optional[Dict[str, Any]]]:
    """Resolves and validates a hook callback and its arguments.

    Args:
        hook: Hook function or source.
        hook_kwargs: The arguments to pass to the hook.
        allow_exception_arg: Whether to allow an implicit exception argument
            to be passed to the hook.

    Returns:
        Tuple of hook source and validated hook arguments converted to JSON-safe
        values.

    Raises:
        ValueError: If `hook_func` is not a valid callable.
        HookValidationException: If hook validation fails.
    """
    # Resolve the hook function
    if isinstance(hook, (str, Source)):
        func = source_utils.load(hook)
    else:
        func = hook

    if not callable(func):
        raise ValueError(f"{func} is not a valid function.")

    # Validate hook arguments
    try:
        hook_args = ()
        if allow_exception_arg:
            hook_args = (Exception(),)
        hook_kwargs = hook_kwargs or {}
        config = ConfigDict(arbitrary_types_allowed=allow_exception_arg)
        validated_kwargs = validate_function_args(
            func, config, *hook_args, **hook_kwargs
        )
    except (ValidationError, TypeError) as e:
        raise HookValidationException(
            f"Failed to validate hook arguments for {func}: {e}\n"
            "Please observe the following guidelines:\n"
            "- the success hook takes no arguments\n"
            "- the failure hook takes a single `BaseException` typed argument\n"
            "- the init hook takes any number of JSON-safe arguments\n"
            "- the cleanup hook takes no arguments\n"
        )

    return source_utils.resolve(func), validated_kwargs


def load_and_run_hook(
    hook_source: "Source",
    hook_parameters: Optional[Dict[str, Any]] = None,
    step_exception: Optional[BaseException] = None,
    raise_on_error: bool = False,
) -> Any:
    """Loads hook source and runs the hook.

    Args:
        hook_source: The source of the hook function.
        hook_parameters: The parameters of the hook function.
        step_exception: The exception of the original step.
        raise_on_error: Whether to raise an error if the hook fails.

    Returns:
        The return value of the hook function.

    Raises:
        RuntimeError: If the hook fails and raise_on_error is True.
    """
    try:
        hook = source_utils.load(hook_source)
    except Exception as e:
        msg = f"Failed to load hook source '{hook_source}' with exception: {e}"
        if raise_on_error:
            raise RuntimeError(msg) from e
        else:
            logger.error(msg)
            return None
    try:
        # Validate hook arguments
        hook_args: Tuple[Any, ...] = ()
        if step_exception:
            hook_args = (step_exception,)
        hook_parameters = hook_parameters or {}
        config = ConfigDict(arbitrary_types_allowed=step_exception is not None)
        validated_kwargs = validate_function_args(
            hook, config, *hook_args, **hook_parameters
        )
    except (ValueError, TypeError) as e:
        msg = (
            f"Failed to validate hook arguments for {hook}: {e}\n"
            "Please observe the following guidelines:\n"
            "- the success hook takes no arguments\n"
            "- the failure hook takes a single `BaseException` typed argument\n"
            "- the init hook takes any number of JSON-safe arguments\n"
            "- the cleanup hook takes no arguments\n"
        )
        if raise_on_error:
            raise RuntimeError(msg) from e
        else:
            logger.error(msg)
            return None

    try:
        logger.debug(f"Running hook {hook} with params: {validated_kwargs}")
        return hook(**validated_kwargs)
    except Exception as e:
        msg = (
            f"Failed to run hook '{hook_source}' with params: "
            f"{validated_kwargs} with exception: '{e}'"
        )
        if raise_on_error:
            raise RuntimeError(msg) from e
        else:
            logger.error(msg)
            return None
