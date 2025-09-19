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

import inspect
import json
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel

from zenml.config.source import Source
from zenml.exceptions import HookValidationException
from zenml.logger import get_logger
from zenml.steps.utils import resolve_type_annotation
from zenml.utils import source_utils

logger = get_logger(__name__)


if TYPE_CHECKING:
    from zenml.types import HookSpecification, InitHookSpecification


def _is_json_safe_scalar_type(type_hint: Optional[Type[Any]]) -> bool:
    """Check if a type is a JSON-safe scalar type.

    Args:
        type_hint: The type to check.

    Returns:
        True if the type is JSON-safe scalar (int, float, str, bool), False otherwise.
    """
    if type_hint is None:
        return False

    # Handle Union types (e.g., Optional[int] = Union[int, None])
    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        # For Optional types, check the non-None type
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _is_json_safe_scalar_type(non_none_args[0])

    # Check basic JSON-safe types
    return type_hint in (int, float, str, bool)


def _is_json_safe_collection_type(type_hint: Optional[Type[Any]]) -> bool:
    """Check if a type is a JSON-safe collection type (list, dict).

    Args:
        type_hint: The type to check.

    Returns:
        True if the type is JSON-safe collection, False otherwise.
    """
    if type_hint is None:
        return False

    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _is_json_safe_collection_type(non_none_args[0])

    # Check for generic list/dict types
    if origin in (list, dict):
        return True

    # Check for bare list/dict types
    return type_hint in (list, dict)


def _is_pydantic_model_type(type_hint: Optional[Type[Any]]) -> bool:
    """Check if a type is a Pydantic BaseModel subclass.

    Args:
        type_hint: The type to check.

    Returns:
        True if the type is a Pydantic BaseModel subclass, False otherwise.
    """
    if type_hint is None:
        return False

    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _is_pydantic_model_type(non_none_args[0])

    try:
        return inspect.isclass(type_hint) and issubclass(type_hint, BaseModel)
    except TypeError:
        return False


def _is_exception_type(type_hint: Optional[Type[Any]]) -> bool:
    """Check if a type is a BaseException subclass.

    Args:
        type_hint: The type to check.

    Returns:
        True if the type is a BaseException subclass, False otherwise.
    """
    if type_hint is None:
        return False

    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _is_exception_type(non_none_args[0])

    try:
        return inspect.isclass(type_hint) and issubclass(
            type_hint, BaseException
        )
    except TypeError:
        return False


def _validate_input_type(
    input_value: Any,
    param_name: str,
    expected_type: Optional[Type[Any]] = None,
) -> Any:
    """Validate and convert input value according to expected type.

    Args:
        input_value: The input value to validate.
        param_name: The parameter name (for error messages).
        expected_type: The expected parameter type.

    Returns:
        The validated/converted value.

    Raises:
        HookValidationException: If validation fails.
    """
    if expected_type is None:
        # No type annotation - allow any JSON-safe value
        resolved_type = type(input_value)
    else:
        resolved_type = resolve_type_annotation(expected_type)

    # Handle Pydantic models (only if type annotation is provided)
    if expected_type and _is_pydantic_model_type(resolved_type):
        if isinstance(input_value, dict):
            try:
                # Convert dict to Pydantic model and then to JSON-safe dict
                model_instance = resolved_type(**input_value)
                return model_instance.model_dump(mode="json")
            except Exception as e:
                raise HookValidationException(
                    f"Failed to convert dict to Pydantic model '{resolved_type.__name__}' "
                    f"for parameter '{param_name}': {e}"
                )
        elif isinstance(input_value, BaseModel):
            # Already a Pydantic model, convert to JSON-safe dict
            return input_value.model_dump(mode="json")
        else:
            raise HookValidationException(
                f"Parameter '{param_name}' expects Pydantic model but got "
                f"{type(input_value)}"
            )

    # Handle JSON-safe scalar types
    if _is_json_safe_scalar_type(resolved_type):
        if not isinstance(input_value, (int, float, str, bool, type(None))):
            raise HookValidationException(
                f"Parameter '{param_name}' expects {resolved_type} but got {type(input_value)}"
            )
        # Additional type checking for specific types
        if resolved_type is not type(input_value) and input_value is not None:
            # Allow some type coercion for JSON-safe types
            try:
                if resolved_type is int and isinstance(
                    input_value, (int, float)
                ):
                    return int(input_value)
                elif resolved_type is float and isinstance(
                    input_value, (int, float)
                ):
                    return float(input_value)
                elif resolved_type is str and isinstance(input_value, str):
                    return input_value
                elif resolved_type is bool and isinstance(input_value, bool):
                    return input_value
                else:
                    raise HookValidationException(
                        f"Parameter '{param_name}' expects {resolved_type} but got {type(input_value)}"
                    )
            except (ValueError, TypeError) as e:
                raise HookValidationException(
                    f"Cannot convert value for parameter '{param_name}': {e}"
                )
        return input_value

    # Handle JSON-safe collection types
    if _is_json_safe_collection_type(resolved_type):
        if resolved_type is list and not isinstance(input_value, list):
            raise HookValidationException(
                f"Parameter '{param_name}' expects list but got {type(input_value)}"
            )
        elif resolved_type is dict and not isinstance(input_value, dict):
            raise HookValidationException(
                f"Parameter '{param_name}' expects dict but got {type(input_value)}"
            )

        # Validate that the collection is JSON-serializable
        try:
            json.dumps(input_value)
            return input_value
        except (TypeError, ValueError) as e:
            raise HookValidationException(
                f"Parameter '{param_name}' contains non-JSON-serializable data: {e}"
            )

    # Unsupported type
    raise HookValidationException(
        f"Parameter '{param_name}' has unsupported type '{resolved_type}'. "
        f"Only JSON-safe types (int, float, str, bool, list, dict) and "
        f"Pydantic models are allowed."
    )


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
        Tuple of hook source and validated hook arguments.

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

    # Get function signature
    sig = inspect.getfullargspec(func)

    # Validate hook arguments
    try:
        validated_kwargs = _validate_hook_arguments(
            sig, hook_kwargs, allow_exception_arg
        )
    except HookValidationException as e:
        raise HookValidationException(
            f"Failed to validate hook arguments for {func}: {e}"
        )

    return source_utils.resolve(func), validated_kwargs


def _validate_hook_arguments(
    sig: inspect.FullArgSpec,
    hook_kwargs: Optional[Dict[str, Any]] = None,
    allow_exception_arg: bool = False,
) -> Dict[str, Any]:
    """Validate hook arguments against function signature.

    Args:
        sig: The function signature specification.
        hook_kwargs: The hook arguments to validate.
        allow_exception_arg: Whether to allow BaseException parameters.

    Returns:
        Dictionary of validated hook arguments.

    Raises:
        HookValidationException: If validation fails.
    """
    args = sig.args.copy()
    annotations = sig.annotations
    defaults: Tuple[Any, ...] = sig.defaults or ()
    hook_kwargs = hook_kwargs or {}

    # Remove 'self' parameter if present (for bound methods)
    if args and args[0] == "self":
        args.pop(0)

    # Calculate which parameters have default values
    num_defaults = len(defaults)
    required_params = set(args[:-num_defaults] if num_defaults > 0 else args)
    all_params = set(args)

    validated_kwargs: Dict[str, Any] = {}
    used_inputs = set()

    # Validate each provided input
    for param_name, input_value in hook_kwargs.items():
        if param_name not in all_params:
            if not sig.varkw:
                # Parameter not in signature and no **kwargs
                raise HookValidationException(
                    f"Hook function does not accept parameter '{param_name}'. "
                    f"Available parameters: {list(all_params)}"
                )

            # Hook accepts **kwargs, validate the extra input
            validated_kwargs[param_name] = _validate_input_type(
                input_value, param_name
            )
            used_inputs.add(param_name)
            continue

        # Parameter matches function signature
        param_type = annotations.get(param_name, None)
        resolved_type = (
            resolve_type_annotation(param_type) if param_type else None
        )

        # Validate and convert the input value
        validated_kwargs[param_name] = _validate_input_type(
            input_value,
            param_name,
            param_type,
        )
        used_inputs.add(param_name)

    # Check for missing required parameters
    provided_params = set(hook_kwargs.keys()) & all_params
    missing_required = required_params - provided_params

    # Filter out BaseException parameters from missing required check
    # as they are handled separately during hook execution
    filtered_missing = set()
    exception_param_count = 0
    for param in missing_required:
        param_type = annotations.get(param, None)
        resolved_type = (
            resolve_type_annotation(param_type) if param_type else None
        )
        if _is_exception_type(resolved_type):
            if not allow_exception_arg:
                raise HookValidationException(
                    f"Parameter '{param}' has BaseException type but "
                    f"exceptions are not allowed for this hook."
                )
            exception_param_count += 1
            if exception_param_count > 1:
                raise HookValidationException(
                    f"Only one BaseException parameter is allowed per hook, "
                    f"but found multiple: {param}"
                )
            continue
        filtered_missing.add(param)

    if filtered_missing:
        raise HookValidationException(
            f"Missing required parameters: {sorted(filtered_missing)}"
        )

    return validated_kwargs


def parse_hook_inputs(
    hook: Callable[..., Any],
    hook_inputs: Optional[Dict[str, Any]] = None,
    step_exception: Optional[BaseException] = None,
) -> Dict[str, Any]:
    """Parses the inputs for a hook function.

    Args:
        hook: The hook function.
        hook_inputs: The inputs of the hook function.
        step_exception: The exception of the original step.

    Returns:
        The parsed inputs for the hook function.
    """
    hook_spec = inspect.getfullargspec(inspect.unwrap(hook))

    function_params: Dict[str, Any] = {}
    hook_inputs = hook_inputs or {}
    used_inputs = set()
    args = hook_spec.args
    annotations = hook_spec.annotations

    if args and args[0] == "self":
        args.pop(0)

    for arg in args:
        arg_type = annotations.get(arg, None)
        resolved_type = resolve_type_annotation(arg_type) if arg_type else None

        # Handle BaseException parameters - inject step_exception
        if resolved_type and issubclass(resolved_type, BaseException):
            function_params[arg] = step_exception
            continue

        # Check if input is provided
        if arg in hook_inputs:
            input_value = hook_inputs[arg]
            used_inputs.add(arg)

            # Convert dict to Pydantic model if needed
            converted_value = _convert_hook_input_value(
                input_value, resolved_type, arg
            )
            function_params[arg] = converted_value

    # Handle extra inputs that don't match any parameter
    extra_inputs = set(hook_inputs.keys()) - used_inputs
    if extra_inputs:
        if hook_spec and hook_spec.varkw:
            # Hook accepts **kwargs, add extra inputs
            for extra_key in extra_inputs:
                function_params[extra_key] = hook_inputs[extra_key]
        else:
            logger.error(
                f"Hook function does not accept **kwargs but extra inputs were "
                f"provided: {list(extra_inputs)}. Hook parameters: {args}"
            )

    return function_params


def _convert_hook_input_value(
    input_value: Any, resolved_type: Optional[Type[Any]], param_name: str
) -> Any:
    """Converts hook input value to the appropriate type.

    Args:
        input_value: The input value to convert.
        resolved_type: The resolved parameter type.
        param_name: The parameter name (for logging).

    Returns:
        The converted value.
    """
    # For scalar values, no conversion needed
    if not isinstance(input_value, dict):
        return input_value

    # If no type annotation, return as-is
    if not resolved_type:
        return input_value

    # Check if the resolved type is a Pydantic model
    if inspect.isclass(resolved_type) and issubclass(resolved_type, BaseModel):
        try:
            # Convert dict to Pydantic model
            return resolved_type(**input_value)
        except Exception as e:
            logger.error(
                f"Failed to convert dict to Pydantic model '{resolved_type.__name__}' "
                f"for parameter '{param_name}': {e}"
            )
            return input_value
    else:
        # For other types, log an error if it's not a scalar
        logger.error(
            f"Hook parameter '{param_name}' has unsupported type '{resolved_type}' "
            f"for dict input. Only scalar values and Pydantic models are supported."
        )
        return input_value


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

        function_params = parse_hook_inputs(
            hook=hook,
            hook_inputs=hook_parameters,
            step_exception=step_exception,
        )
    except Exception as e:
        msg = f"Failed to load hook source '{hook_source}' with exception: {e}"
        if raise_on_error:
            raise RuntimeError(msg) from e
        else:
            logger.error(msg)
            return None

    try:
        logger.debug(f"Running hook {hook} with params: {function_params}")
        return hook(**function_params)
    except Exception as e:
        msg = (
            f"Failed to run hook '{hook_source}' with params: "
            f"{function_params} with exception: '{e}'"
        )
        if raise_on_error:
            raise RuntimeError(msg) from e
        else:
            logger.error(msg)
            return None
