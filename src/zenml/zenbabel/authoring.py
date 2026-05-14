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
"""Experimental authoring helpers for ZenBabel portable JSON steps.

This module is deliberately small scaffolding, not a stable TypeScript SDK. It
lets a Python-authored static pipeline keep a normal placeholder step in the
pipeline graph while compilation swaps that placeholder's execution metadata for
a portable JSON step description.
"""

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Mapping, Sequence, Union

import zenml.pipelines.pipeline_definition as pipeline_definition_module
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.step_configurations import Step
from zenml.execution.pipeline.utils import submit_pipeline
from zenml.models import PipelineSnapshotResponse
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.zenbabel.external_spec import (
    ExternalPipelineOutput,
    ExternalPipelineSpec,
    ExternalPortableStep,
)
from zenml.zenbabel.importer import ExternalSpecLike, build_steps

PipelineOutputLike = Union[
    ExternalPipelineOutput, Mapping[str, str], tuple[str, str]
]
SnapshotValidator = Callable[[PipelineSnapshotResponse], None]


class ExperimentalPortableStepCompiler(Compiler):
    """Compiler bridge that donates portable metadata to placeholders."""

    def __init__(self, portable_steps: Mapping[str, Step]) -> None:
        """Initialize the compiler bridge.

        Args:
            portable_steps: Portable metadata donor steps keyed by invocation id.
        """
        super().__init__()
        self._portable_steps = portable_steps

    def _compile_step_invocation(self, *args: Any, **kwargs: Any) -> Step:
        """Compile normally, then route selected invocations to ZenBabel."""
        compiled_step = super()._compile_step_invocation(*args, **kwargs)
        portable_step = self._portable_steps.get(
            compiled_step.spec.invocation_id
        )
        if portable_step is None:
            return compiled_step

        return _replace_with_portable_execution(
            compiled_step=compiled_step,
            portable_step=portable_step,
        )


@contextmanager
def experimental_portable_json_compiler_bridge(
    external_spec: ExternalSpecLike,
) -> Iterator[None]:
    """Temporarily route placeholder steps through ZenBabel portable JSON.

    Args:
        external_spec: External ZenBabel spec containing portable step metadata.
    """
    original_compiler = pipeline_definition_module.Compiler
    portable_steps = build_steps(external_spec)

    def compiler_factory() -> ExperimentalPortableStepCompiler:
        return ExperimentalPortableStepCompiler(portable_steps=portable_steps)

    pipeline_definition_module.Compiler = compiler_factory  # type: ignore[assignment]
    try:
        yield
    finally:
        pipeline_definition_module.Compiler = original_compiler


def experimental_portable_json_step(
    *,
    name: str,
    command: Sequence[str],
    source_identity: str,
    inputs: Mapping[str, Any] | None = None,
    depends_on: Sequence[str] | None = None,
    parameters: Mapping[str, Any] | None = None,
    parameter_schema: Mapping[str, Any] | None = None,
    outputs: Sequence[str] = ("output",),
) -> ExternalPortableStep:
    """Create a minimal experimental TypeScript portable JSON step spec.

    Args:
        name: Placeholder invocation id in the Python pipeline.
        command: Command to run inside the step container.
        source_identity: Stable TypeScript source identity for hashes/debugging.
        inputs: Optional portable input references.
        depends_on: Optional explicit upstream dependencies.
        parameters: Optional portable JSON parameters.
        parameter_schema: Optional JSON-schema-like parameter schema.
        outputs: Declared output names. Defaults to the normal ZenML ``output``.

    Returns:
        A validated external portable step model.
    """
    return ExternalPortableStep(
        name=name,
        command=list(command),
        source_identity=source_identity,
        inputs=dict(inputs or {}),
        depends_on=list(depends_on or []),
        parameters=dict(parameters or {}),
        parameter_schema=dict(parameter_schema or {})
        if parameter_schema is not None
        else None,
        outputs=list(outputs),
    )


def experimental_portable_json_pipeline_spec(
    *,
    name: str,
    steps: Sequence[ExternalPortableStep],
    outputs: Sequence[PipelineOutputLike] | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> ExternalPipelineSpec:
    """Create a minimal experimental external spec for a static pipeline.

    Args:
        name: Pipeline name.
        steps: Portable step specs keyed to Python placeholder invocations.
        outputs: Optional pipeline outputs.
        parameters: Optional pipeline-level parameters.

    Returns:
        A validated external pipeline spec model.
    """
    return ExternalPipelineSpec(
        name=name,
        steps=list(steps),
        outputs=[_coerce_pipeline_output(output) for output in outputs or []],
        parameters=dict(parameters or {}),
    )


def experimental_compile_snapshot(
    pipeline: Any,
    external_spec: ExternalSpecLike,
) -> Any:
    """Compile a pipeline while the portable JSON bridge is active.

    Args:
        pipeline: ZenML pipeline object to compile.
        external_spec: External ZenBabel spec containing portable step metadata.

    Returns:
        The compiled, not-yet-persisted pipeline snapshot.
    """
    with experimental_portable_json_compiler_bridge(external_spec):
        pipeline.prepare()
        snapshot, _, _ = pipeline._compile()

    return snapshot


def experimental_create_snapshot(
    pipeline: Any,
    external_spec: ExternalSpecLike,
) -> PipelineSnapshotResponse:
    """Create a persisted pipeline snapshot with portable JSON metadata.

    Args:
        pipeline: ZenML pipeline object to snapshot.
        external_spec: External ZenBabel spec containing portable step metadata.

    Returns:
        The persisted pipeline snapshot returned by the active ZenML store.
    """
    with experimental_portable_json_compiler_bridge(external_spec):
        pipeline.prepare()
        return pipeline._create_snapshot()


def experimental_submit_pipeline(
    pipeline: Any,
    external_spec: ExternalSpecLike,
    *,
    snapshot_validator: SnapshotValidator | None = None,
) -> PipelineSnapshotResponse:
    """Create and submit a portable JSON pipeline snapshot.

    Args:
        pipeline: ZenML pipeline object to submit.
        external_spec: External ZenBabel spec containing portable step metadata.
        snapshot_validator: Optional callback invoked after snapshot creation and
            before submission. This is useful while servers may still strip
            experimental fields during persistence.

    Returns:
        The submitted pipeline snapshot.
    """
    snapshot = experimental_create_snapshot(
        pipeline=pipeline,
        external_spec=external_spec,
    )
    if snapshot_validator is not None:
        snapshot_validator(snapshot)

    run = create_placeholder_run(snapshot=snapshot)
    submit_pipeline(
        snapshot=snapshot,
        stack=Client().active_stack,
        placeholder_run=run,
    )
    return snapshot


def _replace_with_portable_execution(
    *,
    compiled_step: Step,
    portable_step: Step,
) -> Step:
    """Copy only portable routing metadata onto a compiled placeholder step."""
    patched_spec = compiled_step.spec.model_copy(
        update={
            "source": portable_step.spec.source,
            "execution_spec": portable_step.spec.execution_spec,
        }
    )
    return compiled_step.model_copy(update={"spec": patched_spec})


def _coerce_pipeline_output(
    output: PipelineOutputLike,
) -> ExternalPipelineOutput:
    """Coerce authoring-friendly output declarations to external models."""
    if isinstance(output, ExternalPipelineOutput):
        return output
    if isinstance(output, tuple):
        step, output_name = output
        return ExternalPipelineOutput(step=step, output=output_name)

    return ExternalPipelineOutput.model_validate(output)


__all__ = [
    "ExperimentalPortableStepCompiler",
    "experimental_compile_snapshot",
    "experimental_create_snapshot",
    "experimental_portable_json_compiler_bridge",
    "experimental_portable_json_pipeline_spec",
    "experimental_portable_json_step",
    "experimental_submit_pipeline",
]
