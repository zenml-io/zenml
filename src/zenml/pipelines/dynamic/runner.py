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
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from zenml import ExternalArtifact
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.step_configurations import Step
from zenml.exceptions import RunStoppedException
from zenml.logger import get_logger
from zenml.logging.step_logging import setup_pipeline_logging
from zenml.models import (
    ArtifactVersionResponse,
    PipelineRunResponse,
    PipelineSnapshotResponse,
)
from zenml.models.v2.core.step_run import StepRunResponse
from zenml.orchestrators.publish_utils import (
    publish_failed_pipeline_run,
    publish_successful_pipeline_run,
)
from zenml.orchestrators.step_launcher import StepLauncher
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

    def __getitem__(self, key: str) -> Any:
        return self.load()[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.load())

    def __len__(self) -> int:
        return len(self.load())

    def __contains__(self, item: Any) -> bool:
        return item in self.load()


class DynamicPipelineRunner:
    def __init__(
        self,
        snapshot: "PipelineSnapshotResponse",
        run: Optional["PipelineRunResponse"],
    ) -> None:
        self._snapshot = snapshot
        self._run = run
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._pipeline: Optional["DynamicPipeline"] = None
        self._orchestrator = Stack.from_model(snapshot.stack).orchestrator
        self._orchestrator_run_id = (
            self._orchestrator.get_orchestrator_run_id()
        )
        self._futures: List[StepRunOutputsFuture] = []

    @property
    def pipeline(self) -> "DynamicPipeline":
        if self._pipeline is None:
            self._pipeline = self._load_pipeline()
        return self._pipeline

    def _load_pipeline(self) -> "DynamicPipeline":
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
        return pipeline

    def run_pipeline(self) -> None:
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
                self.await_all_futures()
                publish_successful_pipeline_run(run.id)

    def run_step_sync(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
        ] = None,
    ) -> StepRunOutputs:
        step = step.copy()
        inputs, upstream_steps = _prepare_step_run(step, args, kwargs, after)
        compiled_step, _ = _compile_step(
            self._snapshot, self.pipeline, step, id, upstream_steps, inputs
        )
        step_run = _run_step_sync(
            snapshot=self._snapshot,
            step=compiled_step,
            orchestrator_run_id=self._orchestrator_run_id,
            retry=_should_retry_locally(
                compiled_step,
                self._snapshot.pipeline_configuration.docker_settings,
            ),
        )
        return _load_step_outputs(step_run.id)

    def run_step_in_thread(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
        ] = None,
    ) -> StepRunOutputsFuture:
        step = step.copy()
        inputs, upstream_steps = _prepare_step_run(step, args, kwargs, after)
        compiled_step, invocation_id = _compile_step(
            self._snapshot, self.pipeline, step, id, upstream_steps, inputs
        )

        def _run() -> StepRunOutputs:
            step_run = _run_step_sync(
                snapshot=self._snapshot,
                step=compiled_step,
                orchestrator_run_id=self._orchestrator_run_id,
                retry=_should_retry_locally(
                    compiled_step,
                    self._snapshot.pipeline_configuration.docker_settings,
                ),
            )
            return _load_step_outputs(step_run.id)

        ctx = contextvars.copy_context()
        future = self._executor.submit(ctx.run, _run)
        step_run_future = StepRunOutputsFuture(
            wrapped=future, invocation_id=invocation_id
        )
        self._futures.append(step_run_future)
        return step_run_future

    def await_all_futures(self) -> None:
        for future in self._futures:
            future.wait()
        self._futures = []


def _prepare_step_run(
    step: "BaseStep",
    args: Tuple[Any],
    kwargs: Dict[str, Any],
    after: Union[
        "StepRunOutputsFuture", Sequence["StepRunOutputsFuture"], None
    ] = None,
) -> Tuple[Dict[str, Any], Set[str]]:
    """Prepare a step run.

    Args:
        step: The step to prepare.
        args: The arguments for the step function.
        kwargs: The keyword arguments for the step function.
        after: The step run output futures to wait for.

    Returns:
        A tuple containing the inputs and the upstream steps.

    Raises:
        ValueError: If an invalid step function input was passed.
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
    validated_args = signature.bind_partial(*args, **kwargs).arguments

    return validated_args, upstream_steps


def _compile_step(
    snapshot: "PipelineSnapshotResponse",
    pipeline: "DynamicPipeline",
    step: "BaseStep",
    id: Optional[str],
    upstream_steps: Optional[Set[str]],
    inputs: Dict[str, Any],
) -> Tuple["Step", str]:
    input_artifacts = {}
    external_artifacts = {}
    for name, value in inputs.items():
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
            external_artifacts[name] = ExternalArtifact(value=value)

    if template := get_config_template(snapshot, step, pipeline):
        step._configuration = template.config.model_copy(
            update={"template": template.spec.invocation_id}
        )

    _, _, _, _, _, default_parameters = step._parse_call_args(**inputs)
    invocation_id = pipeline.add_step_invocation(
        step=step,
        custom_id=id,
        allow_id_suffix=not id,
        input_artifacts=input_artifacts,
        external_artifacts=external_artifacts,
        upstream_steps=upstream_steps,
        parameters={},
        default_parameters=default_parameters,
        model_artifacts_or_metadata={},
        client_lazy_loaders={},
    )
    compiled_step = Compiler()._compile_step_invocation(
        invocation=pipeline.invocations[invocation_id],
        stack=Client().active_stack,
        step_config=None,
        pipeline_configuration=pipeline.configuration,
    )

    return compiled_step, invocation_id


def _run_step_sync(
    snapshot: "PipelineSnapshotResponse",
    step: "Step",
    orchestrator_run_id: str,
    retry: bool = False,
) -> StepRunResponse:
    """Run a step in the active thread.

    Args:
        snapshot: The snapshot.
        step: The step to run.
        orchestrator_run_id: The orchestrator run ID.
        retry: Whether to retry the step if it fails.

    Returns:
        The step run response.
    """

    def _launch_step() -> StepRunResponse:
        launcher = StepLauncher(
            snapshot=snapshot,
            step=step,
            orchestrator_run_id=orchestrator_run_id,
        )
        return launcher.launch()

    if not retry:
        step_run = _launch_step()
    else:
        retries = 0
        retry_config = step.config.retry
        max_retries = retry_config.max_retries if retry_config else 0
        delay = retry_config.delay if retry_config else 0
        backoff = retry_config.backoff if retry_config else 1

        while retries <= max_retries:
            try:
                step_run = _launch_step()
            except RunStoppedException:
                # Don't retry if the run was stopped
                raise
            except BaseException:
                retries += 1
                if retries <= max_retries:
                    logger.info(
                        "Sleeping for %d seconds before retrying step `%s`.",
                        delay,
                        step.config.name,
                    )
                    time.sleep(delay)
                    delay *= backoff
                else:
                    if max_retries > 0:
                        logger.error(
                            "Failed to run step `%s` after %d retries.",
                            step.config.name,
                            max_retries,
                        )
                    raise
            else:
                break

    return step_run


def _load_step_outputs(step_run_id: UUID) -> StepRunOutputs:
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

    if not Client().active_stack.orchestrator.supports_dynamic_out_of_process_steps:
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
