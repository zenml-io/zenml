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
"""Input resolution helpers for dynamic pipeline execution."""

import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Sequence,
    Tuple,
    Union,
)

from zenml.execution.pipeline.dynamic.outputs import (
    AnyOutputFuture,
    ArtifactFuture,
    BaseStepFuture,
    MapResultsFuture,
    PipelineFuture,
    PipelineRunOutputs,
    StepFuture,
    wrap_step_failure,
)
from zenml.execution.pipeline.dynamic.utils import collect_futures
from zenml.models import ArtifactVersionResponse


def _await_input_future(
    future: AnyOutputFuture, return_result: bool = True
) -> Any:
    """Wait for a future used implicitly as a step input.

    Args:
        future: The future to wait for.
        return_result: Whether to return the resolved result or only wait.

    Raises:
        StepExecutionException: If a step future failed.
        Exception: If a non-step future failed.

    Returns:
        The resolved result if `return_result` is True, otherwise None.
    """  # noqa: DOC502, DOC503
    # A child pipeline failure is not a step failure, so it propagates raw.
    if isinstance(future, PipelineFuture):
        if return_result:
            return future.result()
        future.wait()
        return None

    try:
        if return_result:
            return future.result()
        future.wait()
        return None
    except Exception as exc:
        wrapped = wrap_step_failure(exc, invocation_id=future.invocation_id)
        if wrapped is exc:
            raise
        raise wrapped


def _resolve_single_child_pipeline_artifact(
    outputs: PipelineRunOutputs, key: str
) -> ArtifactVersionResponse:
    """Extract the single output artifact from a child pipeline result.

    Inspects the actual outputs rather than the declared output count. This
    matters for unannotated child pipeline entrypoints, whose
    `PipelineFuture.__len__` is `0` even when the pipeline returns exactly one
    artifact at runtime.

    Args:
        outputs: The resolved child pipeline outputs.
        key: The step input name, used in the error message.

    Raises:
        RuntimeError: If the child pipeline did not produce exactly one
            output artifact.

    Returns:
        The single output artifact produced by the child pipeline.
    """
    if isinstance(outputs, ArtifactVersionResponse):
        return outputs
    if isinstance(outputs, tuple) and len(outputs) == 1:
        return outputs[0]

    actual_count = 0 if outputs is None else len(outputs)
    raise RuntimeError(
        f"Invalid step input `{key}`: a child pipeline future used as a "
        f"step input must produce exactly one output artifact, but the "
        f"child pipeline produced {actual_count}."
    )


def convert_to_keyword_arguments(
    func: Callable[..., Any],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    apply_defaults: bool = False,
) -> Dict[str, Any]:
    """Convert function arguments to keyword arguments.

    Args:
        func: The function to convert the arguments to keyword arguments for.
        args: The arguments to convert to keyword arguments.
        kwargs: The keyword arguments to convert to keyword arguments.
        apply_defaults: Whether to apply the function default values.

    Returns:
        The keyword arguments.
    """
    signature = inspect.signature(func, follow_wrapped=True)
    bound_args = signature.bind_partial(*args, **kwargs)
    if apply_defaults:
        bound_args.apply_defaults()

    return bound_args.arguments


def await_step_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Await the inputs of a step.

    Args:
        inputs: The inputs of the step.

    Raises:
        RuntimeError: If a step run future or a child pipeline future referring
            to multiple output artifacts is passed as an input.

    Returns:
        The awaited inputs.
    """
    result = {}
    for key, value in inputs.items():
        if isinstance(value, MapResultsFuture):
            value = value.futures

        if (
            isinstance(value, (list, tuple))
            and value
            and all(isinstance(item, StepFuture) for item in value)
        ):
            if any(len(item._output_keys) != 1 for item in value):
                raise RuntimeError(
                    f"Invalid step input `{key}`: Passing a future that refers "
                    "to multiple output artifacts as an input to another step "
                    "is not allowed."
                )
            value = [_await_input_future(item) for item in value]
        elif isinstance(value, StepFuture):
            if len(value._output_keys) != 1:
                raise RuntimeError(
                    f"Invalid step input `{key}`: Passing a future that refers "
                    "to multiple output artifacts as an input to another step "
                    "is not allowed."
                )
            value = _await_input_future(value)
        elif (
            isinstance(value, (list, tuple))
            and value
            and all(isinstance(item, PipelineFuture) for item in value)
        ):
            value = [
                _resolve_single_child_pipeline_artifact(
                    _await_input_future(item), key=key
                )
                for item in value
            ]
        elif isinstance(value, PipelineFuture):
            value = _resolve_single_child_pipeline_artifact(
                _await_input_future(value), key=key
            )

        if (
            isinstance(value, (list, tuple))
            and value
            and all(isinstance(item, ArtifactFuture) for item in value)
        ):
            value = [_await_input_future(item) for item in value]

        if isinstance(value, ArtifactFuture):
            value = _await_input_future(value)

        result[key] = value

    return result


def collect_upstream_node_ids(
    inputs: Dict[str, Any],
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None],
) -> List[str]:
    """Collect upstream node IDs from step inputs and `after` futures.

    Args:
        inputs: The step inputs.
        after: Optional upstream futures for explicit ordering.

    Returns:
        The upstream node IDs.
    """
    return [
        future.invocation_id
        for future in collect_futures(inputs=inputs, after=after)
    ]


def get_running_upstream_dependencies(
    inputs: Dict[str, Any],
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None],
) -> List[str]:
    """Get all running upstream dependencies for a step.

    Args:
        inputs: The inputs of the step.
        after: The step run futures to wait for.

    Raises:
        TypeError: If an unexpected future type is passed.

    Returns:
        The list of running upstream dependencies.
    """
    futures = collect_futures(inputs=inputs, after=after)

    dependencies = []

    for future in futures:
        if isinstance(future, MapResultsFuture):
            if future.startup_succeeded:
                for item in future.futures:
                    if item.running():
                        dependencies.append(item.invocation_id)
            elif future.running():
                dependencies.append(future.invocation_id)
        elif isinstance(future, BaseStepFuture):
            if future.running():
                dependencies.append(future.invocation_id)
        elif isinstance(future, PipelineFuture):
            if future.running():
                dependencies.append(future.invocation_id)
        else:
            raise TypeError(f"Unexpected future type: {type(future)}")

    return dependencies
