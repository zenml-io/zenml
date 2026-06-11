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

import copy
import itertools
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
    Tuple,
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
    PipelineRunResponse,
    StepRunResponse,
)
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.execution.pipeline.dynamic.outputs import (
        AnyOutputFuture,
        OutputArtifact,
        PipelineRunOutputs,
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
    after: Optional[Sequence["AnyOutputFuture"]] = None,
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
    after: Optional[Sequence["AnyOutputFuture"]] = None,
    name: Optional[str] = None,
) -> Any: ...


def wait(
    schema: Optional[Any] = None,
    type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
    timeout: int = 600,
    poll_interval: int = 5,
    question: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    after: Optional[Sequence["AnyOutputFuture"]] = None,
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


def load_pipeline_run_outputs(
    run: PipelineRunResponse,
) -> "PipelineRunOutputs":
    """Load output artifacts from a finished pipeline run.

    Args:
        run: The finished pipeline run.

    Returns:
        The pipeline outputs.
    """
    outputs = tuple(run.outputs.values())
    if not outputs:
        return None
    if len(outputs) == 1:
        return outputs[0]
    return outputs


@overload
def collect_futures(
    inputs: Optional[Dict[str, Any]] = ...,
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None] = ...,
    expand_map_results: Literal[True] = ...,
) -> List["AnyOutputFuture"]: ...


@overload
def collect_futures(
    inputs: Optional[Dict[str, Any]] = ...,
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None] = ...,
    expand_map_results: Literal[False] = ...,
) -> List["AnyOutputFuture"]: ...


def collect_futures(
    inputs: Optional[Dict[str, Any]] = None,
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None] = None,
    expand_map_results: bool = False,
) -> List["AnyOutputFuture"]:
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
        PipelineFuture,
        StepFuture,
    )

    VALID_OUTPUT_FUTURE_CLASSES = (
        ArtifactFuture,
        StepFuture,
        MapResultsFuture,
        PipelineFuture,
    )

    futures: List["AnyOutputFuture"] = []

    def _append_future(future: "AnyOutputFuture") -> None:
        if expand_map_results and isinstance(future, MapResultsFuture):
            futures.extend(future.futures)
        else:
            futures.append(future)

    def _collect_input_value(value: Any) -> None:
        if isinstance(value, VALID_OUTPUT_FUTURE_CLASSES):
            _append_future(value)
            return

        if isinstance(value, Sequence) and all(
            isinstance(item, VALID_OUTPUT_FUTURE_CLASSES) for item in value
        ):
            for item in value:
                _append_future(item)
            return

    if inputs:
        for value in inputs.values():
            _collect_input_value(value=value)

    if after is not None:
        if isinstance(after, VALID_OUTPUT_FUTURE_CLASSES):
            _append_future(after)
        elif isinstance(after, Sequence) and all(
            isinstance(item, VALID_OUTPUT_FUTURE_CLASSES) for item in after
        ):
            for item in after:
                _append_future(item)
        else:
            raise TypeError(
                "`after` must be a future or a sequence of futures."
            )

    return futures


def expand_mapped_inputs(
    inputs: Dict[str, Any],
    product: bool = False,
) -> List[Dict[str, Any]]:
    """Find the mapped and unmapped inputs of a step.

    Args:
        inputs: The step function inputs.
        product: Whether to produce a cartesian product of the mapped inputs.

    Raises:
        RuntimeError: If no mapped inputs are found or the input combinations
            are not valid.

    Returns:
        The step inputs.
    """
    from zenml.execution.pipeline.dynamic.outputs import OutputArtifact

    static_inputs: Dict[str, Any] = {}
    mapped_input_names: List[str] = []
    mapped_inputs: List[Tuple["OutputArtifact", ...]] = []

    for key, value in inputs.items():
        if isinstance(value, _Unmapped):
            static_inputs[key] = value.value
        elif isinstance(value, OutputArtifact):
            if value.item_count is None:
                static_inputs[key] = value
            elif value.item_count == 0:
                raise RuntimeError(
                    f"Artifact `{value.id}` has 0 items and cannot be mapped "
                    "over. Wrap it with the `unmapped(...)` function to pass "
                    "the artifact without mapping over it."
                )
            else:
                mapped_input_names.append(key)
                mapped_inputs.append(
                    tuple(
                        value.chunk(index=i) for i in range(value.item_count)
                    )
                )
        elif (
            isinstance(value, ArtifactVersionResponse)
            and value.item_count is not None
        ):
            static_inputs[key] = value
            logger.warning(
                "Received sequence-like artifact for step input `%s`. Mapping "
                "over artifacts that are not step output artifacts is "
                "currently not supported, and the complete artifact will be "
                "passed to all steps. If you want to silence this warning, "
                "wrap your input with the `unmapped(...)` function.",
                key,
            )
        elif (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            # List of step output artifacts, in this case the mapping is over
            # the items of the list
            mapped_input_names.append(key)
            mapped_inputs.append(tuple(value))
        elif isinstance(value, Sequence):
            logger.warning(
                "Received sequence-like data for step input `%s`. Mapping over "
                "data that is not a step output artifact is currently not "
                "supported, and the complete data will be passed to all steps. "
                "If you want to silence this warning, wrap your input with the "
                "`unmapped(...)` function.",
                key,
            )
            static_inputs[key] = value
        else:
            static_inputs[key] = value

    if len(mapped_inputs) == 0:
        raise RuntimeError(
            "No inputs to map over found. When calling `.map(...)` or "
            "`.product(...)` on a step, you need to pass at least one "
            "sequence-like step output of a previous step as input."
        )

    step_inputs = []

    if product:
        for input_combination in itertools.product(*mapped_inputs):
            all_inputs = copy.deepcopy(static_inputs)
            for name, value in zip(mapped_input_names, input_combination):
                all_inputs[name] = value
            step_inputs.append(all_inputs)
    else:
        item_counts = [len(inputs) for inputs in mapped_inputs]
        if not all(count == item_counts[0] for count in item_counts):
            raise RuntimeError(
                f"All mapped input artifacts must have the same "
                "item counts, but you passed artifacts with item counts "
                f"{item_counts}. If you want "
                "to pass sequence-like artifacts without mapping over "
                "them, wrap them with the `unmapped(...)` function."
            )

        for i in range(item_counts[0]):
            all_inputs = copy.deepcopy(static_inputs)
            for name, artifact in zip(
                mapped_input_names,
                [artifact_list[i] for artifact_list in mapped_inputs],
            ):
                all_inputs[name] = artifact
            step_inputs.append(all_inputs)

    return step_inputs


def get_remaining_retries(step_run: "StepRunResponse") -> int:
    """Get the remaining retries for a step run.

    Args:
        step_run: The step run to get the remaining retries for.

    Returns:
        The remaining retries for the step run.
    """
    max_retries = (
        step_run.config.retry.max_retries if step_run.config.retry else 0
    )
    return max(0, 1 + max_retries - step_run.version)
