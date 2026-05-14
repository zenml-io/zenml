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
"""Importer for experimental ZenBabel external specs."""

import hashlib
from typing import Any, Dict, List, Mapping, Union

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import OutputSpec, PipelineSpec
from zenml.config.source import Source
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.config.step_execution_spec import StepExecutionSpec
from zenml.materializers.built_in_materializer import (
    BuiltInContainerMaterializer,
    BuiltInMaterializer,
)
from zenml.models import PipelineSnapshotBase
from zenml.utils import source_utils
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE
from zenml.zenbabel.external_spec import (
    ExternalInput,
    ExternalInputReference,
    ExternalPipelineSpec,
    ExternalPortableStep,
    _iter_input_references,
    _iter_upstream_step_names,
    _topological_step_names,
)

ExternalSpecLike = Union[ExternalPipelineSpec, Mapping[str, Any]]


def build_steps(external_spec: ExternalSpecLike) -> Dict[str, Step]:
    """Build normal ZenML step objects from an external spec.

    Args:
        external_spec: External ZenBabel spec model or dictionary.

    Returns:
        ZenML step objects keyed by invocation/step name.
    """
    spec = _coerce_external_spec(external_spec)
    steps_by_name = {step.name: step for step in spec.steps}

    return {
        step_name: _build_step(steps_by_name[step_name])
        for step_name in _topological_step_names(spec.steps)
    }


def build_pipeline_spec(external_spec: ExternalSpecLike) -> PipelineSpec:
    """Build a normal ZenML pipeline spec from an external spec.

    Args:
        external_spec: External ZenBabel spec model or dictionary.

    Returns:
        A ZenML pipeline spec that can use conditional portable-step
        serialization.
    """
    spec = _coerce_external_spec(external_spec)
    steps = build_steps(spec)

    return PipelineSpec(
        steps=[step.spec for step in steps.values()],
        outputs=[
            OutputSpec(step_name=output.step, output_name=output.output)
            for output in spec.outputs
        ],
        parameters=spec.parameters,
    )


def build_pipeline_snapshot(
    external_spec: ExternalSpecLike,
    *,
    run_name_template: str | None = None,
    client_environment: Dict[str, Any] | None = None,
    client_version: str | None = None,
    server_version: str | None = None,
) -> PipelineSnapshotBase:
    """Build a minimal ZenML pipeline snapshot from an external spec.

    Args:
        external_spec: External ZenBabel spec model or dictionary.
        run_name_template: Optional run name template. Defaults to the pipeline
            name.
        client_environment: Optional client environment metadata.
        client_version: Optional ZenML client version.
        server_version: Optional ZenML server version.

    Returns:
        A static ``PipelineSnapshotBase`` with ZenML configuration, steps and
        pipeline spec populated.
    """
    spec = _coerce_external_spec(external_spec)
    steps = build_steps(spec)
    pipeline_spec = build_pipeline_spec(spec)

    return PipelineSnapshotBase(
        run_name_template=run_name_template or spec.name,
        is_dynamic=False,
        pipeline_configuration=PipelineConfiguration(name=spec.name),
        step_configurations=steps,
        client_environment=client_environment or {},
        client_version=client_version,
        server_version=server_version,
        pipeline_version_hash=_compute_pipeline_version_hash(pipeline_spec),
        pipeline_spec=pipeline_spec,
    )


def _coerce_external_spec(
    external_spec: ExternalSpecLike,
) -> ExternalPipelineSpec:
    """Validate or return an external spec model."""
    if isinstance(external_spec, ExternalPipelineSpec):
        return external_spec

    return ExternalPipelineSpec.model_validate(external_spec)


def _build_step(external_step: ExternalPortableStep) -> Step:
    """Build one ZenML step from one external portable step."""
    config = StepConfiguration(
        name=external_step.name,
        parameters=external_step.parameters,
        outputs={
            output_name: {
                "materializer_source": _portable_json_materializer_sources(),
            }
            for output_name in external_step.outputs
        },
    )

    return Step(
        spec=StepSpec(
            source=PORTABLE_STEP_ADAPTER_SOURCE,
            upstream_steps=sorted(
                set(_iter_upstream_step_names(external_step))
            ),
            inputs=_build_inputs(external_step.inputs),
            invocation_id=external_step.name,
            parameter_spec=external_step.parameter_schema,
            execution_spec=StepExecutionSpec(
                language=external_step.language,
                protocol=external_step.protocol,
                command=external_step.command,
                source_identity=external_step.source_identity,
            ),
        ),
        config=config,
        step_config_overrides=config,
    )


def _build_inputs(
    inputs: Mapping[str, ExternalInput],
) -> Dict[str, Union[InputSpec, List[InputSpec]]]:
    """Build ZenML input specs from external input references."""
    return {
        input_name: _build_input(input_value)
        for input_name, input_value in inputs.items()
    }


def _build_input(
    input_value: ExternalInput,
) -> Union[InputSpec, List[InputSpec]]:
    """Build one ZenML input spec or input-spec collection."""
    if isinstance(input_value, list):
        return [_build_scalar_input(reference) for reference in input_value]

    return _build_scalar_input(input_value)


def _build_scalar_input(reference: ExternalInputReference) -> InputSpec:
    """Build one scalar ZenML input spec."""
    return InputSpec(step_name=reference.step, output_name=reference.output)


def _portable_json_materializer_sources() -> tuple[Source, ...]:
    """Return built-in materializer sources for strict portable JSON values."""
    return (
        source_utils.resolve(BuiltInMaterializer),
        source_utils.resolve(BuiltInContainerMaterializer),
    )


def _compute_pipeline_version_hash(pipeline_spec: PipelineSpec) -> str:
    """Compute a stable importer-local snapshot hash."""
    hash_ = hashlib.sha256()
    hash_.update(pipeline_spec.json_with_string_sources.encode())
    return hash_.hexdigest()


__all__ = [
    "build_pipeline_snapshot",
    "build_pipeline_spec",
    "build_steps",
]
