#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Dynamic pipeline execution utilities."""

import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from zenml.client import Client
from zenml.enums import ExecutionStatus, RunWaitConditionType
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
    StepRunResponse,
)
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.execution.pipeline.dynamic.outputs import (
        AnyStepFuture,
        BaseStepFuture,
        OutputArtifact,
        StepRunOutputs,
    )

logger = get_logger(__name__)


T = TypeVar("T")


class _Unmapped(Generic[T]):
    """Wrapper class for inputs that should not be mapped over."""

    def __init__(self, value: T):
        """Initialize the wrapper.

        Args:
            value: The value to wrap.
        """
        self.value = value


def unmapped(value: T) -> _Unmapped[T]:
    """Helper function to pass an input without mapping over it.

    Wrap any step input with this function and then pass it to `step.map(...)`
    to pass the full value to all steps.

    Args:
        value: The value to wrap.

    Returns:
        The wrapped value.
    """
    return _Unmapped(value)


@overload
def wait(
    schema: Type[T],
    type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
    timeout: int = 600,
    poll_interval: int = 5,
    question: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    after: Optional[Sequence["AnyStepFuture"]] = None,
    name: Optional[str] = None,
) -> T: ...


@overload
def wait(
    schema: object = None,
    type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
    timeout: int = 600,
    poll_interval: int = 5,
    question: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    after: Optional[Sequence["AnyStepFuture"]] = None,
    name: Optional[str] = None,
) -> Any: ...


def wait(
    schema: Optional[Any] = None,
    type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
    timeout: int = 600,
    poll_interval: int = 5,
    question: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    after: Optional[Sequence["AnyStepFuture"]] = None,
    name: Optional[str] = None,
) -> Any:
    """Pause dynamic execution on an external wait condition.

    Args:
        schema: Optional expected output type for the resolved result.
        type: Wait condition type.
        timeout: Maximum time in seconds to poll before pausing.
        poll_interval: Poll interval in seconds.
        question: Optional question shown to external actors.
        metadata: Optional metadata attached to the condition.
        after: Optional upstream futures that must finish before waiting.
        name: Optional deterministic wait condition name.

    Raises:
        RuntimeError: If called outside of dynamic pipeline execution.

    Returns:
        The resolved wait condition value.
    """
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )

    context = DynamicPipelineRunContext.get()
    if not context:
        raise RuntimeError(
            "`zenml.wait(...)` can only be used inside dynamic pipelines."
        )

    return context.runner.wait(
        schema=schema,
        type=type,
        timeout=timeout,
        poll_interval=poll_interval,
        question=question,
        after=after,
        metadata=metadata,
        name=name,
    )


def wait_for_step_run_to_finish(step_run_id: UUID) -> "StepRunResponse":
    """Wait until a step run is finished.

    Args:
        step_run_id: The ID of the step run.

    Returns:
        The finished step run.
    """
    sleep_interval = 1
    max_sleep_interval = 64

    while True:
        step_run = Client().zen_store.get_run_step(step_run_id)

        if step_run.status != ExecutionStatus.RUNNING:
            return step_run

        logger.debug(
            "Waiting for step run with ID %s to finish (current status: %s)",
            step_run_id,
            step_run.status,
        )
        time.sleep(sleep_interval)
        if sleep_interval < max_sleep_interval:
            sleep_interval *= 2


def get_latest_step_run(
    pipeline_run_id: UUID, invocation_id: str, hydrate: bool = False
) -> "StepRunResponse":
    """Get the latest step run for a step.

    Args:
        pipeline_run_id: The ID of the pipeline run.
        invocation_id: The invocation ID of the step.
        hydrate: Whether to hydrate the step run.

    Raises:
        RuntimeError: If no step run exists for the given invocation ID.

    Returns:
        The latest step run.
    """
    step_runs = Client().list_run_steps(
        pipeline_run_id=pipeline_run_id,
        name=invocation_id,
        exclude_retried=True,
        size=1,
        hydrate=hydrate,
    )

    if not step_runs:
        raise RuntimeError(
            f"Step `{invocation_id}` not found in pipeline run "
            f"`{pipeline_run_id}`."
        )

    return step_runs.items[0]


def wait_for_step_to_finish(
    pipeline_run_id: UUID, step_name: str
) -> "StepRunResponse":
    """Wait until a step is finished.

    Args:
        pipeline_run_id: The ID of the pipeline run.
        step_name: The name of the step.

    Returns:
        The finished step run.
    """
    sleep_interval = 1
    max_sleep_interval = 64

    while True:
        step_run = get_latest_step_run(
            pipeline_run_id, step_name, hydrate=False
        )
        # If a step is in `retrying` status, another step run will be
        # created and we will try to pick it up in the next iteration.
        if step_run.status not in {
            ExecutionStatus.RUNNING,
            ExecutionStatus.RETRYING,
        }:
            return step_run

        logger.debug(
            "Waiting for step `%s` to finish (current status: %s)",
            step_name,
            step_run.status,
        )

        time.sleep(sleep_interval)
        if sleep_interval < max_sleep_interval:
            sleep_interval *= 2


def load_step_run_outputs(step_run_id: UUID) -> "StepRunOutputs":
    """Load the outputs of a step run.

    Args:
        step_run_id: The ID of the step run.

    Returns:
        The outputs of the step run.
    """
    from zenml.execution.pipeline.dynamic.outputs import OutputArtifact

    step_run = Client().zen_store.get_run_step(step_run_id)

    def _convert_output_artifact(
        output_name: str, artifact: "ArtifactVersionResponse"
    ) -> "OutputArtifact":
        return OutputArtifact(
            output_name=output_name,
            step_name=step_run.name,
            **artifact.model_dump(),
        )

    output_artifacts = step_run.regular_outputs
    if len(output_artifacts) == 0:
        return None
    elif len(output_artifacts) == 1:
        name, artifact = next(iter(output_artifacts.items()))
        return _convert_output_artifact(output_name=name, artifact=artifact)
    else:
        # Make sure we return them in the same order as they're defined in the
        # step configuration, as we don't enforce any ordering in the DB.
        outputs = []

        for template_name in step_run.config.outputs.keys():
            name = string_utils.format_name_template(
                template_name,
                substitutions=step_run.config.substitutions,
            )
            outputs.append(
                _convert_output_artifact(
                    output_name=template_name, artifact=output_artifacts[name]
                )
            )

        return tuple(outputs)


@overload
def collect_futures(
    inputs: Optional[Dict[str, Any]] = ...,
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = ...,
    expand_map_results: Literal[True] = ...,
) -> List["BaseStepFuture"]: ...


@overload
def collect_futures(
    inputs: Optional[Dict[str, Any]] = ...,
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = ...,
    expand_map_results: Literal[False] = ...,
) -> List["AnyStepFuture"]: ...


def collect_futures(
    inputs: Optional[Dict[str, Any]] = None,
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
    expand_map_results: bool = False,
) -> Union[List["BaseStepFuture"], List["AnyStepFuture"]]:
    """Collect futures referenced in step inputs and `after`.

    Args:
        inputs: Optional step inputs to inspect for futures.
        after: Optional explicit upstream dependencies. Must be a future or a
            sequence containing only futures.
        expand_map_results: Whether map futures should be expanded into their
            child step futures.

    Raises:
        TypeError: If `after` is not a future or a sequence containing only
            futures.

    Returns:
        The collected futures.
    """
    from zenml.execution.pipeline.dynamic.outputs import (
        ArtifactFuture,
        MapResultsFuture,
        StepFuture,
    )

    VALID_FUTURE_CLASSES = (ArtifactFuture, StepFuture, MapResultsFuture)

    futures: List["AnyStepFuture"] = []

    def _append_future(future: "AnyStepFuture") -> None:
        if expand_map_results and isinstance(future, MapResultsFuture):
            futures.extend(future.futures)
        else:
            futures.append(future)

    def _collect_input_value(value: Any) -> None:
        if isinstance(value, VALID_FUTURE_CLASSES):
            _append_future(value)
            return

        if isinstance(value, Sequence) and all(
            isinstance(item, VALID_FUTURE_CLASSES) for item in value
        ):
            for item in value:
                _append_future(item)
            return

    if inputs:
        for value in inputs.values():
            _collect_input_value(value=value)

    if after:
        if isinstance(after, VALID_FUTURE_CLASSES):
            _append_future(after)
        elif isinstance(after, Sequence) and all(
            isinstance(item, VALID_FUTURE_CLASSES) for item in after
        ):
            for item in after:
                _append_future(item)
        else:
            raise TypeError(
                "`after` must be a future or a sequence of futures."
            )

    return futures
