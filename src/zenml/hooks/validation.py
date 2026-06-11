#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Hook resolution and argument validation."""

import inspect
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
from zenml.utils import source_utils
from zenml.utils.pydantic_utils import validate_function_args

if TYPE_CHECKING:
    from zenml.types import HookSpecification, InitHookSpecification


def bind_optional_hook_args(
    func: Callable[..., Any], candidate_args: Tuple[Any, ...]
) -> Tuple[Any, ...]:
    """Binds as many leading candidate arguments as the signature accepts.

    Args:
        func: The hook function.
        candidate_args: Candidate arguments in order.

    Returns:
        The leading candidate arguments the signature can accept.
    """
    from zenml.steps.utils import get_resolved_signature

    signature = get_resolved_signature(func)
    positional = 0
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            return candidate_args

        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional += 1

    return candidate_args[:positional]


def resolve_and_validate_hook(
    hook: Union["HookSpecification", "InitHookSpecification"],
    *args: Any,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Tuple[Source, Dict[str, Any]]:
    """Resolve a hook and validate it can be called with the given arguments.

    Args:
        hook: Hook function or source.
        *args: Positional arguments offered to the hook. Only the leading
            arguments the signature accepts are bound and validated.
        kwargs: Keyword arguments passed to the hook.

    Raises:
        ValueError: If `hook` is not a valid callable.
        HookValidationException: If the hook cannot accept the arguments.

    Returns:
        The hook source and the validated, JSON-safe keyword arguments.
    """
    func = source_utils.load(hook) if isinstance(hook, (str, Source)) else hook
    if not callable(func):
        raise ValueError(f"{func} is not a valid function.")

    bound_args = bind_optional_hook_args(func, args)
    # Allow arbitrary types if an exception arg is provided. If validating an
    # init hook which allows user-provided arguments, we only allow
    # JSON-serializable arguments.
    config = ConfigDict(arbitrary_types_allowed=bool(bound_args))
    try:
        validated_kwargs = validate_function_args(
            func, config, *bound_args, **(kwargs or {})
        )
    except (ValidationError, TypeError) as e:
        raise HookValidationException(
            f"Failed to validate hook arguments for {func}: {e}\n"
            "Please observe the following guidelines:\n"
            "- the success hook takes no arguments\n"
            "- the failure hook optionally takes a single `BaseException`"
            " argument\n"
            "- the on_start hook takes no arguments\n"
            "- the on_end hook optionally takes a single `BaseException`"
            " argument\n"
            "- the on_pause hook takes no arguments\n"
            "- the on_resume hook takes no arguments\n"
            "- the init hook takes any number of JSON-safe arguments\n"
            "- the cleanup hook takes no arguments\n"
        ) from e

    return source_utils.resolve(func), validated_kwargs
