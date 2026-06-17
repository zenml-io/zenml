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
"""Compilation helpers for dynamic pipelines."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from zenml import ExternalArtifact
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.constants import DOCKER_SETTINGS_KEY
from zenml.config.step_configurations import (
    Step,
    StepConfiguration,
    StepConfigurationUpdate,
)
from zenml.enums import StepRuntime
from zenml.execution.pipeline.dynamic.inputs import (
    _await_input_future,
    await_step_inputs,
    convert_to_keyword_arguments,
)
from zenml.execution.pipeline.dynamic.outputs import (
    AnyOutputFuture,
    OutputArtifact,
    PipelineFuture,
)
from zenml.execution.pipeline.dynamic.utils import collect_futures
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
    CodeReferenceRequest,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
)
from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
from zenml.steps import BaseStep
from zenml.steps.entrypoint_function_utils import StepArtifact
from zenml.steps.step_invocation import StepInvocation
from zenml.steps.utils import OutputSignature

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.orchestrators import BaseOrchestrator


logger = get_logger(__name__)


def compile_dynamic_step_invocation(
    snapshot: "PipelineSnapshotResponse",
    pipeline: "DynamicPipeline",
    step: "BaseStep",
    invocation_id: str,
    inputs: Dict[str, Any],
    pipeline_docker_settings: "DockerSettings",
    after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None] = None,
    config: Optional[StepConfigurationUpdate] = None,
) -> "Step":
    """Compile a dynamic step invocation.

    Args:
        snapshot: The snapshot.
        pipeline: The dynamic pipeline.
        step: The step to compile.
        invocation_id: The invocation ID of the step.
        inputs: The inputs for the step function.
        pipeline_docker_settings: The Docker settings of the parent pipeline.
        after: The step run output futures to wait for.
        config: The configuration for the step.

    Returns:
        The compiled step.
    """
    upstream_steps = set()

    for future in collect_futures(after=after, expand_map_results=True):
        _await_input_future(future, return_result=False)
        if isinstance(future, PipelineFuture):
            # A pipeline future means we're waiting for a child pipeline to
            # finish. No such step exists in our pipeline, so we can't track
            # it as an upstream step.
            continue
        upstream_steps.add(future.invocation_id)

    inputs = await_step_inputs(inputs)

    for value in inputs.values():
        if isinstance(value, OutputArtifact):
            upstream_steps.add(value.step_name)

        if (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            upstream_steps.update(item.step_name for item in value)

    input_artifacts: Dict[str, Union[StepArtifact, List[StepArtifact]]] = {}
    external_artifacts = {}
    for name, value in inputs.items():
        if isinstance(value, OutputArtifact):
            input_artifacts[name] = StepArtifact(
                invocation_id=value.step_name,
                output_name=value.output_name,
                annotation=OutputSignature(resolved_annotation=Any),
                pipeline=pipeline,
                chunk_index=value.chunk_index,
                chunk_size=value.chunk_size,
            )
        elif (
            isinstance(value, list)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            input_artifacts[name] = [
                StepArtifact(
                    invocation_id=item.step_name,
                    output_name=item.output_name,
                    annotation=OutputSignature(resolved_annotation=Any),
                    pipeline=pipeline,
                    chunk_index=item.chunk_index,
                    chunk_size=item.chunk_size,
                )
                for item in value
            ]
        elif isinstance(value, (ArtifactVersionResponse, ExternalArtifact)):
            external_artifacts[name] = value
        else:
            # TODO: should some of these be parameters?
            external_artifacts[name] = ExternalArtifact(value=value)

    if template := get_config_template(snapshot, step, pipeline):
        logger.debug(
            "Using config template `%s` for step `%s`",
            template.spec.invocation_id,
            invocation_id,
        )
        step._configuration = template.config.model_copy(
            update={"template": template.spec.invocation_id}
        )

    default_parameters = {
        key: value
        for key, value in convert_to_keyword_arguments(
            step.entrypoint, (), inputs, apply_defaults=True
        ).items()
        if key not in inputs and key not in step.configuration.parameters
    }

    step_invocation = StepInvocation(
        id=invocation_id,
        step=step,
        input_artifacts=input_artifacts,
        external_artifacts=external_artifacts,
        default_parameters=default_parameters,
        upstream_steps=upstream_steps,
        pipeline=pipeline,
        model_artifacts_or_metadata={},
        client_lazy_loaders={},
        parameters={},
    )

    compiled_step = Compiler()._compile_step_invocation(
        invocation=step_invocation,
        stack=Client().active_stack,
        step_config=config,
        pipeline=pipeline,
    )

    if not compiled_step.config.docker_settings.skip_build:
        if template:
            if (
                template.config.docker_settings
                != compiled_step.config.docker_settings
            ):
                logger.warning(
                    "Custom Docker settings specified for step %s will be "
                    "ignored. The image built for template %s will be used "
                    "instead.",
                    invocation_id,
                    template.spec.invocation_id,
                )
        elif compiled_step.config.docker_settings != pipeline_docker_settings:
            logger.warning(
                "Custom Docker settings specified for step %s will be "
                "ignored. The image built for the pipeline will be used "
                "instead.",
                invocation_id,
            )

    return compiled_step


def compile_child_pipeline(
    pipeline: "DynamicPipeline",
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    parent_snapshot: "PipelineSnapshotResponse",
) -> "PipelineSnapshotResponse":
    """Compile and persist a snapshot for a dynamic child pipeline run.

    The child snapshot inherits the parent build/code context so child
    execution runs in the same orchestration environment.

    Args:
        pipeline: The child dynamic pipeline
        args: Positional arguments for the child pipeline.
        kwargs: Keyword arguments for the child pipeline.
        parent_snapshot: Snapshot of the parent dynamic run.

    Raises:
        RuntimeError: If the parent snapshot has no stack.

    Returns:
        The persisted child snapshot.
    """
    if parent_snapshot.stack is None:
        raise RuntimeError(
            "Cannot compile a child pipeline snapshot: parent snapshot has no "
            "associated stack."
        )

    inputs = convert_to_keyword_arguments(
        pipeline.entrypoint, tuple(args), kwargs
    )
    inputs = await_step_inputs(inputs)
    pipeline.prepare(**inputs)

    snapshot_base, _, _ = pipeline._compile()

    code_reference = None
    if parent_snapshot.code_reference:
        code_reference = CodeReferenceRequest(
            commit=parent_snapshot.code_reference.commit,
            subdirectory=parent_snapshot.code_reference.subdirectory,
            code_repository=parent_snapshot.code_reference.code_repository.id,
        )

    # The child pipeline will use the parent's build, so we simply copy the Docker
    # settings from the parent snapshot.
    snapshot_base.pipeline_configuration.settings[DOCKER_SETTINGS_KEY] = (
        parent_snapshot.pipeline_configuration.docker_settings.model_copy()
    )
    for _, step_configuration in snapshot_base.step_configurations.items():
        step_configuration.config.settings.pop(DOCKER_SETTINGS_KEY, None)
        step_configuration.step_config_overrides.settings.pop(
            DOCKER_SETTINGS_KEY, None
        )

    request = PipelineSnapshotRequest(
        project=parent_snapshot.project_id,
        stack=parent_snapshot.stack.id,
        pipeline=pipeline.register().id,
        build=parent_snapshot.build.id if parent_snapshot.build else None,
        code_reference=code_reference,
        code_path=parent_snapshot.code_path,
        source_code=pipeline.source_code,
        **snapshot_base.model_dump(),
    )
    return Client().zen_store.create_snapshot(snapshot=request)


def get_step_runtime(
    step_config: "StepConfiguration",
    pipeline_docker_settings: "DockerSettings",
    orchestrator: Optional["BaseOrchestrator"] = None,
) -> StepRuntime:
    """Determine if a step should be run in process.

    Args:
        step_config: The step configuration.
        pipeline_docker_settings: The Docker settings of the parent pipeline.
        orchestrator: The orchestrator to use. If not provided, the
            orchestrator will be inferred from the active stack.

    Returns:
        The runtime for the step.
    """
    if step_config.step_operator:
        return StepRuntime.ISOLATED

    if not orchestrator:
        orchestrator = Client().active_stack.orchestrator

    if not orchestrator.can_run_isolated_steps:
        return StepRuntime.INLINE

    runtime = step_config.runtime

    if runtime is None:
        if not step_config.resource_settings.empty:
            runtime = StepRuntime.ISOLATED
        elif step_config.docker_settings != pipeline_docker_settings:
            runtime = StepRuntime.ISOLATED
        else:
            runtime = StepRuntime.INLINE

    return runtime


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
