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
"""Experimental external ZenBabel pipeline spec models."""

from typing import Any, Dict, Iterable, List, Mapping, Union

from pydantic import Field, field_validator, model_validator

from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.step_execution_spec import (
    StepExecutionLanguage,
    StepExecutionProtocol,
)


def _validate_name(value: str, field_name: str) -> str:
    """Validate a non-empty spec identifier.

    Args:
        value: The identifier to validate.
        field_name: Human-readable field name for error messages.

    Raises:
        ValueError: If the value is empty.

    Returns:
        The validated value.
    """
    if not value:
        raise ValueError(f"ZenBabel external spec `{field_name}` is empty.")

    return value


class ExternalInputReference(FrozenBaseModel):
    """Reference to an upstream step output in an external spec."""

    step: str
    output: str = "output"

    @field_validator("step")
    @classmethod
    def _validate_step(cls, step: str) -> str:
        """Validate the referenced step name."""
        return _validate_name(step, "input.step")

    @field_validator("output")
    @classmethod
    def _validate_output(cls, output: str) -> str:
        """Validate the referenced output name."""
        return _validate_name(output, "input.output")


ExternalInput = Union[ExternalInputReference, List[ExternalInputReference]]


class ExternalPipelineOutput(FrozenBaseModel):
    """Pipeline-level output exported from an external spec."""

    step: str
    output: str = "output"

    @field_validator("step")
    @classmethod
    def _validate_step(cls, step: str) -> str:
        """Validate the referenced step name."""
        return _validate_name(step, "outputs.step")

    @field_validator("output")
    @classmethod
    def _validate_output(cls, output: str) -> str:
        """Validate the referenced output name."""
        return _validate_name(output, "outputs.output")


class ExternalPortableStep(FrozenBaseModel):
    """Small external spec for one portable TypeScript step."""

    name: str
    command: List[str]
    source_identity: str
    inputs: Dict[str, ExternalInput] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    parameter_schema: Dict[str, Any] | None = None
    outputs: List[str] = Field(default_factory=lambda: ["output"])
    language: StepExecutionLanguage = StepExecutionLanguage.TYPESCRIPT
    protocol: StepExecutionProtocol = (
        StepExecutionProtocol.ZENML_PORTABLE_JSON_V1
    )

    @field_validator("name")
    @classmethod
    def _validate_step_name(cls, name: str) -> str:
        """Validate the step name."""
        return _validate_name(name, "steps.name")

    @field_validator("source_identity")
    @classmethod
    def _validate_source_identity(cls, source_identity: str) -> str:
        """Validate the portable source identity."""
        return _validate_name(source_identity, "steps.source_identity")

    @field_validator("outputs")
    @classmethod
    def _validate_outputs(cls, outputs: List[str]) -> List[str]:
        """Validate output names."""
        if not outputs:
            raise ValueError(
                "ZenBabel portable steps must declare at least one output."
            )

        seen = set()
        for output in outputs:
            _validate_name(output, "steps.outputs")
            if output in seen:
                raise ValueError(
                    f"ZenBabel step output `{output}` is declared twice."
                )
            seen.add(output)

        return outputs

    @field_validator("depends_on")
    @classmethod
    def _validate_depends_on(cls, depends_on: List[str]) -> List[str]:
        """Validate explicit upstream dependencies."""
        seen = set()
        for dependency in depends_on:
            _validate_name(dependency, "steps.depends_on")
            if dependency in seen:
                raise ValueError(
                    "ZenBabel step dependency "
                    f"`{dependency}` is declared twice."
                )
            seen.add(dependency)

        return depends_on

    @field_validator("command")
    @classmethod
    def _validate_command(cls, command: List[str]) -> List[str]:
        """Validate the portable command."""
        if not command:
            raise ValueError(
                "ZenBabel portable step command must not be empty."
            )

        for argument in command:
            if not argument:
                raise ValueError(
                    "ZenBabel portable step command arguments must not be empty."
                )

        return command

    @model_validator(mode="after")
    def _validate_portable_contract(self) -> "ExternalPortableStep":
        """Reject execution contracts outside the v1 importer scope."""
        if self.language != StepExecutionLanguage.TYPESCRIPT:
            raise ValueError(
                "ZenBabel external specs only support TypeScript portable "
                "steps in v1."
            )

        if self.protocol != StepExecutionProtocol.ZENML_PORTABLE_JSON_V1:
            raise ValueError(
                "ZenBabel external specs only support the "
                "zenml-portable-json-v1 protocol in v1."
            )

        return self


class ExternalPipelineSpec(FrozenBaseModel):
    """Small static external pipeline spec accepted by ZenBabel v1."""

    name: str
    graph: str = "static"
    is_dynamic: bool = False
    steps: List[ExternalPortableStep]
    outputs: List[ExternalPipelineOutput] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _validate_pipeline_name(cls, name: str) -> str:
        """Validate the pipeline name."""
        return _validate_name(name, "name")

    @field_validator("graph")
    @classmethod
    def _validate_graph(cls, graph: str) -> str:
        """Reject graph shapes outside the v1 importer scope."""
        if graph != "static":
            raise ValueError(
                "ZenBabel external specs only support static pipelines in v1."
            )

        return graph

    @model_validator(mode="after")
    def _validate_static_pipeline(self) -> "ExternalPipelineSpec":
        """Validate static graph references."""
        if self.is_dynamic:
            raise ValueError(
                "ZenBabel external specs only support static pipelines in v1."
            )

        if not self.steps:
            raise ValueError(
                "ZenBabel external pipeline specs must declare at least one step."
            )

        steps_by_name: Dict[str, ExternalPortableStep] = {}
        for step in self.steps:
            if step.name in steps_by_name:
                raise ValueError(
                    f"ZenBabel step `{step.name}` is declared twice."
                )
            steps_by_name[step.name] = step

        for step in self.steps:
            for upstream_name in _iter_upstream_step_names(step):
                if upstream_name == step.name:
                    raise ValueError(
                        f"ZenBabel step `{step.name}` cannot depend on itself."
                    )
                if upstream_name not in steps_by_name:
                    raise ValueError(
                        f"ZenBabel step `{step.name}` references unknown "
                        f"upstream step `{upstream_name}`."
                    )

            for reference in _iter_input_references(step.inputs):
                upstream_step = steps_by_name[reference.step]
                if reference.output not in upstream_step.outputs:
                    raise ValueError(
                        f"ZenBabel step `{step.name}` references unknown "
                        f"output `{reference.output}` on upstream step "
                        f"`{reference.step}`."
                    )

        for output in self.outputs:
            if output.step not in steps_by_name:
                raise ValueError(
                    "ZenBabel pipeline output references unknown step "
                    f"`{output.step}`."
                )
            if output.output not in steps_by_name[output.step].outputs:
                raise ValueError(
                    "ZenBabel pipeline output references unknown output "
                    f"`{output.output}` on step `{output.step}`."
                )

        _topological_step_names(self.steps)
        return self


def _iter_input_references(
    inputs: Mapping[str, ExternalInput],
) -> Iterable[ExternalInputReference]:
    """Iterate over all input references in a step input mapping."""
    for input_value in inputs.values():
        if isinstance(input_value, list):
            yield from input_value
        else:
            yield input_value


def _iter_upstream_step_names(step: ExternalPortableStep) -> Iterable[str]:
    """Iterate over all explicit and data upstream step names."""
    yield from step.depends_on
    for reference in _iter_input_references(step.inputs):
        yield reference.step


def _topological_step_names(steps: List[ExternalPortableStep]) -> List[str]:
    """Return step names in topological order.

    Args:
        steps: The steps to sort.

    Raises:
        ValueError: If the graph contains a cycle.

    Returns:
        Step names sorted so every upstream appears before its downstream.
    """
    ordered: List[str] = []
    temporary_marks = set()
    permanent_marks = set()
    steps_by_name = {step.name: step for step in steps}

    def visit(step_name: str) -> None:
        if step_name in permanent_marks:
            return
        if step_name in temporary_marks:
            raise ValueError(
                "ZenBabel external specs only support acyclic static "
                "pipelines in v1."
            )

        temporary_marks.add(step_name)
        for upstream_name in sorted(
            set(_iter_upstream_step_names(steps_by_name[step_name]))
        ):
            visit(upstream_name)
        temporary_marks.remove(step_name)
        permanent_marks.add(step_name)
        ordered.append(step_name)

    for step in steps:
        visit(step.name)

    return ordered


__all__ = [
    "ExternalInput",
    "ExternalInputReference",
    "ExternalPipelineOutput",
    "ExternalPipelineSpec",
    "ExternalPortableStep",
]
