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
"""Dynamic pipeline runner."""

import contextvars
import inspect
from concurrent.futures import Future, ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)
from uuid import UUID

from zenml import ExternalArtifact
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.step_configurations import Step
from zenml.execution.step.utils import launch_step
from zenml.logger import get_logger
from zenml.logging.step_logging import setup_pipeline_logging
from zenml.models import (
    ArtifactVersionResponse,
    PipelineRunResponse,
    PipelineSnapshotResponse,
)
from zenml.orchestrators.publish_utils import (
    publish_failed_pipeline_run,
    publish_successful_pipeline_run,
)
from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
from zenml.pipelines.dynamic.run_context import DynamicPipelineRunContext
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.stack import Stack
from zenml.steps.entrypoint_function_utils import StepArtifact
from zenml.steps.utils import OutputSignature
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.config.step_configurations import Step
    from zenml.steps import BaseStep


logger = get_logger(__name__)


class DynamicStepRunOutput(ArtifactVersionResponse):
    """Dynamic step run output artifact."""

    output_name: str
    step_name: str


StepRunOutputs = Union[
    None, DynamicStepRunOutput, Tuple[DynamicStepRunOutput, ...]
]


# TODO: maybe one future per artifact? But for a step that doesn't return anything, the user wouldn't have a future to wait for.
# Or that step returns a future that returns None? Would be similar to a python function.
class StepRunOutputsFuture:
    """Future for a step run output."""

    def __init__(
        self, wrapped: Future[StepRunOutputs], invocation_id: str
    ) -> None:
        """Initialize the future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
        """
        self._wrapped = wrapped
        self._invocation_id = invocation_id

    def wait(self) -> None:
        """Wait for the future to complete."""
        self._wrapped.result()

    def result(self) -> StepRunOutputs:
        """Get the step run output artifacts.

        Returns:
            The step run output artifacts.
        """
        return self._wrapped.result()

    def load(self) -> Any:
        """Get the step run output artifact data.

        Raises:
            ValueError: If the step run output is invalid.

        Returns:
            The step run output artifact data.
        """
        result = self.result()

        if result is None:
            return None
        elif isinstance(result, ArtifactVersionResponse):
            return result.load()
        elif isinstance(result, tuple):
            return tuple(item.load() for item in result)
        else:
            raise ValueError(f"Invalid step run output: {result}")


class DynamicPipelineRunner:
    """Dynamic pipeline runner."""

    def __init__(
        self,
        snapshot: "PipelineSnapshotResponse",
        run: Optional["PipelineRunResponse"],
    ) -> None:
        """Initialize the dynamic pipeline runner.

        Args:
            snapshot: The snapshot of the pipeline.
            run: The pipeline run.

        Raises:
            RuntimeError: If the snapshot has no associated stack.
        """
        if not snapshot.stack:
            raise RuntimeError("Missing stack for snapshot.")
        self._snapshot = snapshot
        self._run = run
        # TODO: make this configurable
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._pipeline: Optional["DynamicPipeline"] = None
        self._orchestrator = Stack.from_model(snapshot.stack).orchestrator
        self._orchestrator_run_id = (
            self._orchestrator.get_orchestrator_run_id()
        )
        self._futures: List[StepRunOutputsFuture] = []

    @property
    def pipeline(self) -> "DynamicPipeline":
        """The pipeline that the runner is executing.

        Raises:
            RuntimeError: If the pipeline can't be loaded.

        Returns:
            The pipeline that the runner is executing.
        """
        if self._pipeline is None:
            if (
                not self._snapshot.pipeline_spec
                or not self._snapshot.pipeline_spec.source
            ):
                raise RuntimeError("Missing pipeline source for snapshot.")

            pipeline = source_utils.load(self._snapshot.pipeline_spec.source)
            if not isinstance(pipeline, DynamicPipeline):
                raise RuntimeError(
                    f"Invalid pipeline source: {self._snapshot.pipeline_spec.source}"
                )
            self._pipeline = pipeline

        return self._pipeline

    def run_pipeline(self) -> None:
        """Run the pipeline."""
        with setup_pipeline_logging(
            source="orchestrator",
            snapshot=self._snapshot,
            run_id=self._run.id if self._run else None,
        ) as logs_request:
            run = self._run or create_placeholder_run(
                snapshot=self._snapshot,
                orchestrator_run_id=self._orchestrator_run_id,
                logs=logs_request,
            )

            assert (
                self._snapshot.pipeline_spec
            )  # Always exists for new snapshots
            pipeline_parameters = self._snapshot.pipeline_spec.parameters

            with DynamicPipelineRunContext(
                pipeline=self.pipeline,
                run=run,
                snapshot=self._snapshot,
                runner=self,
            ):
                self._orchestrator.run_init_hook(snapshot=self._snapshot)
                try:
                    # TODO: step logging isn't threadsafe
                    self.pipeline._call_entrypoint(**pipeline_parameters)
                except:
                    publish_failed_pipeline_run(run.id)
                    raise
                finally:
                    self._orchestrator.run_cleanup_hook(
                        snapshot=self._snapshot
                    )
                self.await_all_step_run_futures()
                publish_successful_pipeline_run(run.id)

    @overload
    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
        ] = None,
        concurrent: Literal[False] = False,
    ) -> StepRunOutputs: ...

    @overload
    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
        ] = None,
        concurrent: Literal[True] = True,
    ) -> "StepRunOutputsFuture": ...

    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
        ] = None,
        concurrent: bool = False,
    ) -> Union[StepRunOutputs, "StepRunOutputsFuture"]:
        """Launch a step.

        Args:
            step: The step to launch.
            id: The invocation ID of the step.
            args: The arguments for the step function.
            kwargs: The keyword arguments for the step function.
            after: The step run output futures to wait for.
            concurrent: Whether to launch the step concurrently.

        Returns:
            The step run outputs or a future for the step run outputs.
        """
        step = step.copy()
        compiled_step = compile_dynamic_step_invocation(
            snapshot=self._snapshot,
            pipeline=self.pipeline,
            step=step,
            id=id,
            args=args,
            kwargs=kwargs,
            after=after,
        )

        def _launch() -> StepRunOutputs:
            step_run = launch_step(
                snapshot=self._snapshot,
                step=compiled_step,
                orchestrator_run_id=self._orchestrator_run_id,
                retry=_should_retry_locally(
                    compiled_step,
                    self._snapshot.pipeline_configuration.docker_settings,
                ),
            )
            return _load_step_run_outputs(step_run.id)

        if concurrent:
            ctx = contextvars.copy_context()
            future = self._executor.submit(ctx.run, _launch)
            step_run_future = StepRunOutputsFuture(
                wrapped=future, invocation_id=compiled_step.spec.invocation_id
            )
            self._futures.append(step_run_future)
            return step_run_future
        else:
            return _launch()

    def await_all_step_run_futures(self) -> None:
        """Await all step run output futures."""
        for future in self._futures:
            future.wait()
        self._futures = []


def compile_dynamic_step_invocation(
    snapshot: "PipelineSnapshotResponse",
    pipeline: "DynamicPipeline",
    step: "BaseStep",
    id: Optional[str],
    args: Tuple[Any],
    kwargs: Dict[str, Any],
    after: Union[
        "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
    ] = None,
) -> "Step":
    """Compile a dynamic step invocation.

    Args:
        snapshot: The snapshot.
        pipeline: The dynamic pipeline.
        step: The step to compile.
        id: Custom invocation ID.
        upstream_steps: The upstream steps.
        inputs: Inputs to the step function.
        default_parameters: Default parameters of the step function.

    Returns:
        The compiled step.
    """
    upstream_steps = set()

    if isinstance(after, StepRunOutputsFuture):
        after.wait()
        upstream_steps.add(after._invocation_id)
    elif isinstance(after, Sequence):
        for item in after:
            item.wait()
            upstream_steps.add(item._invocation_id)

    def _await_and_validate_input(input: Any) -> Any:
        if isinstance(input, StepRunOutputsFuture):
            input = input.result()

        if (
            input
            and isinstance(input, tuple)
            and isinstance(input[0], DynamicStepRunOutput)
        ):
            raise ValueError(
                "Passing multiple step run outputs to another step is not "
                "allowed."
            )

        if isinstance(input, DynamicStepRunOutput):
            upstream_steps.add(input.step_name)

        return input

    args = tuple(_await_and_validate_input(arg) for arg in args)
    kwargs = {
        key: _await_and_validate_input(value) for key, value in kwargs.items()
    }

    # TODO: we can validate the type of the inputs that are passed as raw data
    signature = inspect.signature(step.entrypoint, follow_wrapped=True)
    bound_args = signature.bind_partial(*args, **kwargs)
    validated_args = bound_args.arguments
    bound_args.apply_defaults()
    default_parameters = {
        key: value
        for key, value in bound_args.arguments.items()
        if key not in validated_args
    }

    input_artifacts = {}
    external_artifacts = {}
    for name, value in validated_args.items():
        if isinstance(value, DynamicStepRunOutput):
            input_artifacts[name] = StepArtifact(
                invocation_id=value.step_name,
                output_name=value.output_name,
                annotation=OutputSignature(resolved_annotation=Any),
                pipeline=pipeline,
            )
        elif isinstance(value, (ArtifactVersionResponse, ExternalArtifact)):
            external_artifacts[name] = value
        else:
            # TODO: should some of these be parameters?
            external_artifacts[name] = ExternalArtifact(value=value)

    if template := get_config_template(snapshot, step, pipeline):
        step._configuration = template.config.model_copy(
            update={"template": template.spec.invocation_id}
        )

    invocation_id = pipeline.add_step_invocation(
        step=step,
        custom_id=id,
        allow_id_suffix=not id,
        input_artifacts=input_artifacts,
        external_artifacts=external_artifacts,
        upstream_steps=upstream_steps,
        default_parameters=default_parameters,
        parameters={},
        model_artifacts_or_metadata={},
        client_lazy_loaders={},
    )
    return Compiler()._compile_step_invocation(
        invocation=pipeline.invocations[invocation_id],
        stack=Client().active_stack,
        step_config=None,
        pipeline_configuration=pipeline.configuration,
    )


def _load_step_run_outputs(step_run_id: UUID) -> StepRunOutputs:
    """Load the outputs of a step run.

    Args:
        step_run_id: The ID of the step run.

    Returns:
        The outputs of the step run.
    """
    step_run = Client().zen_store.get_run_step(step_run_id)

    def _convert_output_artifact(
        output_name: str, artifact: ArtifactVersionResponse
    ) -> DynamicStepRunOutput:
        return DynamicStepRunOutput(
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
        return tuple(
            _convert_output_artifact(output_name=name, artifact=artifact)
            for name, artifact in output_artifacts.items()
        )


def _should_retry_locally(
    step: "Step", pipeline_docker_settings: "DockerSettings"
) -> bool:
    """Determine if a step should be retried locally.

    Args:
        step: The step.
        pipeline_docker_settings: The Docker settings of the parent pipeline.

    Returns:
        Whether the step should be retried locally.
    """
    if step.config.step_operator:
        return True

    if should_run_in_process(step, pipeline_docker_settings):
        return True
    else:
        # Running out of process with the orchestrator
        return (
            not Client().active_stack.orchestrator.config.handles_step_retries
        )


def should_run_in_process(
    step: "Step", pipeline_docker_settings: "DockerSettings"
) -> bool:
    """Determine if a step should be run in process.

    Args:
        step: The step.
        pipeline_docker_settings: The Docker settings of the parent pipeline.

    Returns:
        Whether the step should be run in process.
    """
    if step.config.step_operator:
        return False

    if not Client().active_stack.orchestrator.can_launch_dynamic_steps:
        return True

    if step.config.in_process is False:
        return False
    elif step.config.in_process is None:
        if not step.config.resource_settings.empty:
            return False

        if step.config.docker_settings != pipeline_docker_settings:
            return False

    return True


def get_config_template(
    snapshot: "PipelineSnapshotResponse",
    step: "BaseStep",
    pipeline: "DynamicPipeline",
) -> Optional["Step"]:
    """Get the config template for a step executed in a dynamic pipeline.

    Args:
        snapshot: The snapshot of the pipeline.
        step: The step to get the config template for.
        pipeline: The dynamic pipeline that the step is being executed in.

    Returns:
        The config template for the step.
    """
    for index, step_ in enumerate(pipeline.depends_on):
        if step_._static_id == step._static_id:
            break
    else:
        return None

    return list(snapshot.step_configurations.values())[index]
