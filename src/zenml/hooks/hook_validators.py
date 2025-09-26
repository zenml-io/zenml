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
    Callable,
    Dict,
    Optional,
    Tuple,
    Union,
)

from pydantic import ConfigDict, ValidationError

from zenml.config.source import Source
from zenml.exceptions import HookValidationException
from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.pydantic_utils import validate_function_args

logger = get_logger(__name__)


if TYPE_CHECKING:
    from zenml.types import HookSpecification, InitHookSpecification


def _validate_hook_arguments(
    _func: Callable[..., Any],
    hook_kwargs: Dict[str, Any],
    exception_arg: Union[BaseException, bool] = False,
) -> Dict[str, Any]:
    """Validates hook arguments.

    Args:
        _func: The hook function to validate.
        hook_kwargs: The hook keyword arguments to validate.
        exception_arg: The exception argument to validate.

    Returns:
        The validated hook arguments.

    Raises:
        HookValidationException: If the hook arguments are not valid.
    """
    # Validate hook arguments
    try:
        hook_args: Tuple[Any, ...] = ()
        if isinstance(exception_arg, BaseException):
            hook_args = (exception_arg,)
        elif exception_arg is True:
            hook_args = (Exception(),)
        config = ConfigDict(arbitrary_types_allowed=len(hook_args) > 0)
        validated_kwargs = validate_function_args(
            _func, config, *hook_args, **hook_kwargs
        )
    except (ValidationError, TypeError) as e:
        exc_msg = (
            "Failed to validate hook arguments for {func}: {e}\n"
            "Please observe the following guidelines:\n"
            "- the success hook takes no arguments\n"
            "- the failure hook optionally takes a single `BaseException` "
            "typed argument\n"
            "- the init hook takes any number of JSON-safe arguments\n"
            "- the cleanup hook takes no arguments\n"
        )

        if not hook_args:
            raise HookValidationException(exc_msg.format(func=_func, e=e))

        # If we have an exception argument, we try again without it. This is
        # to account for the case where the hook function does not expect an
        # exception argument.
        hook_args = ()
        config = ConfigDict(arbitrary_types_allowed=False)
        try:
            validated_kwargs = validate_function_args(
                _func, config, *hook_args, **hook_kwargs
            )
        except (ValidationError, TypeError) as e:
            raise HookValidationException(exc_msg.format(func=_func, e=e))

    return validated_kwargs


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
    """
    # Resolve the hook function
    if isinstance(hook, (str, Source)):
        func = source_utils.load(hook)
    else:
        func = hook

    if not callable(func):
        raise ValueError(f"{func} is not a valid function.")

    # Validate hook arguments
    validated_kwargs = _validate_hook_arguments(
        func, hook_kwargs or {}, allow_exception_arg
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
        HookValidationException: If hook validation fails.
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
        validated_kwargs = _validate_hook_arguments(
            hook, hook_parameters or {}, step_exception or False
        )
    except HookValidationException as e:
        if raise_on_error:
            raise
        else:
            logger.error(e)
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
