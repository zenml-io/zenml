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
"""Hook execution."""

import re
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Union,
)

from zenml.config.source import Source
from zenml.constants import (
    ENV_ZENML_TRACK_LIFECYCLE_HOOK_OUTPUTS,
    handle_bool_env_var,
)
from zenml.enums import ExecutionStatus, HookType
from zenml.hooks.recording import record_hook_invocation
from zenml.hooks.validation import bind_optional_hook_args
from zenml.logger import get_logger
from zenml.models import ExceptionInfo
from zenml.models.v2.core.hook_invocation import HOOK_NAME_PATTERN
from zenml.utils import async_utils, source_utils
from zenml.utils.exception_utils import collect_exception_information
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.utils.logging_utils import LoggingContext

logger = get_logger(__name__)


def _default_hook_name(
    func: Callable[..., Any], hook_type: HookType
) -> Optional[str]:
    """Derive a default name for a custom hook invocation.

    Args:
        func: The hook function.
        hook_type: The type of the hook invocation.

    Returns:
        The function name for custom hooks when it matches the hook name
        pattern, otherwise None.
    """
    if hook_type is not HookType.CUSTOM:
        return None
    candidate: Optional[str] = getattr(func, "__name__", None)
    if candidate and re.match(HOOK_NAME_PATTERN, candidate):
        return candidate
    return None


def _validate_hook_name(name: Optional[str]) -> None:
    """Validate a hook name.

    Args:
        name: The name of the hook.

    Raises:
        ValueError: If the name is invalid.
    """
    if name is not None and not re.match(HOOK_NAME_PATTERN, name):
        raise ValueError(f"Invalid hook name: {name}")


def _parse_hook_outputs(
    func: Callable[..., Any], result: Any
) -> Dict[str, Any]:
    """Map a hook function return value to named outputs.

    Args:
        func: The hook function.
        result: The return value of the hook function.

    Raises:
        ValueError: If the return value does not match the output annotations.

    Returns:
        Mapping of output names to values.
    """
    from zenml.steps.utils import parse_return_type_annotations

    output_signature = parse_return_type_annotations(func)

    if len(output_signature) == 0:
        return {}

    if len(output_signature) == 1:
        return {next(iter(output_signature)): result}

    if not isinstance(result, (list, tuple)):
        raise ValueError(
            f"Hook function with multiple outputs ({list(output_signature)}) "
            f"must return a tuple or list, got {type(result)}."
        )

    if len(result) != len(output_signature):
        raise ValueError(
            f"Hook function returned {len(result)} values but its annotation "
            f"declares {len(output_signature)} outputs."
        )

    return dict(zip(output_signature.keys(), result))


def _get_log_source_name(hook_type: HookType, name: Optional[str]) -> str:
    """Get the log source name for a hook.

    Args:
        hook_type: The type of the hook invocation.
        name: The resolved name of the hook invocation.

    Returns:
        The log source name.
    """
    if hook_type is not HookType.CUSTOM:
        return f"hook:{hook_type.value}"
    if name:
        return f"hook:custom:{name}"
    return "hook:custom"


def setup_hook_logging_context(
    hook_type: HookType,
    name: Optional[str],
) -> Optional["LoggingContext"]:
    """Setup a logging context that captures a hook's output.

    Args:
        hook_type: The type of the hook invocation.
        name: The resolved name of the hook invocation.

    Returns:
        The logging context.
    """
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )
    from zenml.steps.step_context import StepContext
    from zenml.utils.logging_utils import (
        is_pipeline_logging_enabled,
        is_step_logging_enabled,
        setup_logging_context,
    )

    try:
        source = _get_log_source_name(hook_type, name)
        step_context = StepContext.get()
        if step_context is not None:
            if is_step_logging_enabled(
                step_configuration=step_context.step_run.config,
                pipeline_configuration=step_context.pipeline_run.config,
            ):
                return setup_logging_context(
                    source=source,
                    step_run=step_context.step_run,
                    pipeline_run=step_context.pipeline_run,
                    block_on_exit=False,
                )
        else:
            run_context = DynamicPipelineRunContext.get()
            if run_context is not None and is_pipeline_logging_enabled(
                pipeline_configuration=run_context.run.config,
            ):
                return setup_logging_context(
                    source=source,
                    pipeline_run=run_context.run,
                    block_on_exit=False,
                )
    except Exception as e:
        logger.debug("Failed to set up hook logging context: %s", e)
    return None


def run_hook(
    func: Union[Callable[..., Any], Source],
    *args: Any,
    kwargs: Optional[Dict[str, Any]] = None,
    name: Optional[str] = None,
    hook_type: HookType = HookType.CUSTOM,
    store_return: bool = False,
    track: bool = True,
) -> Any:
    """Run a hook, optionally recording the invocation.

    Args:
        func: The hook function or a source to load it from.
        *args: Positional arguments for the hook function.
        kwargs: Keyword arguments for the hook function.
        name: Custom event name for the invocation.
        hook_type: Type of the hook invocation.
        store_return: Whether to materialize the return value as outputs.
        track: Whether to record the invocation.

    Raises:
        BaseException: Any exception raised by the hook function.

    Returns:
        The return value of the hook function.
    """
    if isinstance(func, Source):
        loaded_func = source_utils.load(func)
        import_path: Optional[str] = func.import_path
    else:
        loaded_func = func
        try:
            import_path = source_utils.resolve(func).import_path
        except Exception:
            import_path = None

    _validate_hook_name(name)
    resolved_name = name or _default_hook_name(loaded_func, hook_type)

    start_time = utc_now()
    status = ExecutionStatus.COMPLETED
    outputs: Optional[Dict[str, Any]] = None
    exception_info: Optional[ExceptionInfo] = None

    logs_context = setup_hook_logging_context(hook_type, resolved_name)
    logs_id = logs_context.log_model.id if logs_context is not None else None

    with logs_context or nullcontext():
        try:
            try:
                if async_utils.is_async_callable(loaded_func):
                    result = async_utils.run_coroutine_isolated(
                        loaded_func(*args, **(kwargs or {}))
                    )
                else:
                    result = loaded_func(*args, **(kwargs or {}))
            except BaseException as e:
                status = ExecutionStatus.FAILED
                exception_info = collect_exception_information(
                    e, user_func=loaded_func
                )
                raise
            # Output parsing runs after the hook succeeded, so a parsing error
            # does not mark the invocation as FAILED or discard the hook's
            # status.
            if store_return:
                outputs = _parse_hook_outputs(loaded_func, result)
            return result
        finally:
            if track:
                try:
                    record_hook_invocation(
                        name=resolved_name,
                        hook_type=hook_type,
                        source=import_path,
                        outputs=outputs,
                        start_time=start_time,
                        end_time=utc_now(),
                        status=status,
                        exception_info=exception_info,
                        logs_id=logs_id,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to record `%s` hook invocation: %s",
                        hook_type.value,
                        e,
                    )


def run_lifecycle_hook(
    hook_source: Optional[Source],
    hook_type: HookType,
    optional_args: Optional[Tuple[Any, ...]] = None,
) -> None:
    """Run a configured lifecycle hook, recording it and swallowing errors.

    Args:
        hook_source: The source of the hook function, or None to do nothing.
        hook_type: The type of the lifecycle hook.
        optional_args: Candidate arguments offered to the hook in order. As
            many leading arguments as the hook signature accepts are bound.
    """
    if hook_source is None:
        return

    # The signature was already validated when the hook was configured, so we
    # only bind the leading values it accepts and run it.
    try:
        func = source_utils.load(hook_source)
        bound_args = bind_optional_hook_args(func, optional_args or ())
        store_return = handle_bool_env_var(
            ENV_ZENML_TRACK_LIFECYCLE_HOOK_OUTPUTS, default=False
        )
        run_hook(
            func, *bound_args, hook_type=hook_type, store_return=store_return
        )
    except Exception as e:
        logger.error(
            "Failed to run `%s` hook from source `%s`: %s",
            hook_type.value,
            hook_source,
            e,
        )
