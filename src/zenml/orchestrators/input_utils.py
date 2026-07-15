#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utilities for inputs."""

from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Tuple, Union

from zenml.client import Client
from zenml.config.step_configurations import (
    ArtifactVersionInputSource,
    ClientCallInputSource,
    InputSource,
    LiteralInputSource,
    ModelDataInputSource,
    Step,
)
from zenml.enums import StepRunInputArtifactType
from zenml.exceptions import InputResolutionError
from zenml.utils import string_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import (
        StepRunInputResponse,
        StepRunInputValue,
    )


def resolve_step_inputs(
    step: "Step",
    pipeline_run: "PipelineRunResponse",
    step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    input_overrides: Optional[Mapping[str, "InputSource"]] = None,
) -> Tuple[
    Dict[str, List["StepRunInputResponse"]], Dict[str, "StepRunInputValue"]
]:
    """Resolves inputs for the current step.

    Args:
        step: The step for which to resolve the inputs.
        pipeline_run: The current pipeline run.
        step_runs: A dictionary of already fetched step runs to use for input
            resolution. This will be updated in-place with newly fetched step
            runs.
        input_overrides: The input source overrides for the step.

    Raises:
        InputResolutionError: If input resolving failed due to a missing
            step or output.

    Returns:
        The input artifact versions and the resolved non-artifact input
        values.
    """
    from zenml.models.v2.core.step_run import (
        StepRunInputResponse,
        StepRunInputValue,
    )
    from zenml.orchestrators.step_run_utils import fetch_step_runs_by_names

    step_runs = step_runs or {}
    input_overrides = input_overrides or {}

    steps_to_fetch = set(
        input_.step_name
        for name, input_list in step.spec.normalized_inputs.items()
        if name not in input_overrides
        for input_ in input_list
    )
    # Remove all the step runs that we've already fetched.
    steps_to_fetch.difference_update(step_runs.keys())

    if steps_to_fetch:
        step_runs.update(
            fetch_step_runs_by_names(
                step_run_names=list(steps_to_fetch), pipeline_run=pipeline_run
            )
        )

    input_artifacts: Dict[str, List[StepRunInputResponse]] = {}
    input_values: Dict[str, StepRunInputValue] = {}

    for name, input_list in step.spec.normalized_inputs.items():
        if name in input_overrides:
            continue

        input_artifacts[name] = []
        for index, input_ in enumerate(input_list):
            try:
                step_run = step_runs[input_.step_name]
            except KeyError:
                raise InputResolutionError(
                    f"No step `{input_.step_name}` found in current run."
                )

            output_name = string_utils.format_name_template(
                input_.output_name, substitutions=step_run.substitutions
            )

            try:
                output = step_run.regular_outputs[output_name]
            except KeyError:
                raise InputResolutionError(
                    f"No step output `{output_name}` found for step "
                    f"`{input_.step_name}`."
                )
            except ValueError:
                raise InputResolutionError(
                    f"Expected 1 regular output artifact for {output_name}."
                )

            input_artifacts[name].append(
                StepRunInputResponse(
                    input_type=StepRunInputArtifactType.STEP_OUTPUT,
                    index=index,
                    chunk_index=input_.chunk_index,
                    chunk_size=input_.chunk_size,
                    **output.model_dump(),
                )
            )

    sources: Dict[str, "InputSource"] = {
        **step.config.inputs,
        **input_overrides,
    }

    for name, source in sources.items():
        resolved = _resolve_input_source(
            source=source,
            input_name=name,
            step_name=step.config.name,
            pipeline_run=pipeline_run,
            overridden=name in input_overrides,
        )
        if isinstance(resolved, StepRunInputResponse):
            input_artifacts[name] = [resolved]
        else:
            input_values[name] = resolved

    return input_artifacts, input_values


def _resolve_input_source(
    source: "InputSource",
    input_name: str,
    step_name: str,
    pipeline_run: "PipelineRunResponse",
    overridden: bool,
) -> Union["StepRunInputResponse", "StepRunInputValue"]:
    """Resolve a single input source.

    Args:
        source: The input source to resolve.
        input_name: The name of the input.
        step_name: The name of the step.
        pipeline_run: The current pipeline run.
        overridden: Whether the source comes from a user-provided override.

    Raises:
        ValueError: If the source cannot be resolved.

    Returns:
        The resolved input artifact or the resolved input value.
    """
    from zenml.models import ArtifactVersionResponse
    from zenml.models.v2.core.step_run import (
        StepRunInputResponse,
        StepRunInputValue,
    )

    def _input_type(
        default: StepRunInputArtifactType,
    ) -> StepRunInputArtifactType:
        return StepRunInputArtifactType.OVERRIDE if overridden else default

    if isinstance(source, LiteralInputSource):
        return StepRunInputValue(
            value=source.value, source_type=source.type, overridden=overridden
        )

    if isinstance(source, ArtifactVersionInputSource):
        return StepRunInputResponse(
            input_type=_input_type(StepRunInputArtifactType.EXTERNAL),
            **Client().get_artifact_version(source.id).model_dump(),
        )

    if isinstance(source, ClientCallInputSource):
        value = source.lazy_loader.evaluate()
        if isinstance(value, ArtifactVersionResponse):
            return StepRunInputResponse(
                input_type=_input_type(StepRunInputArtifactType.LAZY_LOADED),
                **value.model_dump(),
            )

        if not yaml_utils.is_json_serializable(value):
            raise ValueError(
                f"Client lazy loader for input `{input_name}` of step "
                f"`{step_name}` resolved to a value that is not JSON "
                "serializable."
            )

        return StepRunInputValue(
            value=value, source_type=source.type, overridden=overridden
        )

    assert isinstance(source, ModelDataInputSource)
    return _resolve_model_data_source(
        source=source,
        input_name=input_name,
        step_name=step_name,
        pipeline_run=pipeline_run,
        overridden=overridden,
    )


def _resolve_model_data_source(
    source: "ModelDataInputSource",
    input_name: str,
    step_name: str,
    pipeline_run: "PipelineRunResponse",
    overridden: bool,
) -> Union["StepRunInputResponse", "StepRunInputValue"]:
    """Resolve a model version data input source.

    Args:
        source: The input source to resolve.
        input_name: The name of the input.
        step_name: The name of the step.
        pipeline_run: The current pipeline run.
        overridden: Whether the source comes from a user-provided override.

    Raises:
        ValueError: If the source cannot be resolved.

    Returns:
        The resolved input artifact or the resolved input value.
    """
    from zenml.models.v2.core.step_run import (
        StepRunInputResponse,
        StepRunInputValue,
    )

    lazy_loader = source.lazy_loader
    error_prefix = (
        f"Failed to lazy load model version data in step `{step_name}` "
        f"input `{input_name}`: "
    )

    try:
        context_model_version = lazy_loader._get_model_response(
            pipeline_run=pipeline_run
        )
    except RuntimeError as e:
        raise ValueError(error_prefix + str(e))

    if lazy_loader.artifact_name is None:
        if (
            lazy_loader.metadata_name
            and context_model_version.run_metadata is not None
        ):
            return StepRunInputValue(
                value=context_model_version.run_metadata[
                    lazy_loader.metadata_name
                ],
                source_type=source.type,
                overridden=overridden,
            )

        raise ValueError(
            error_prefix + "Cannot load artifact from model version, "
            "no artifact name specified."
        )

    artifact_ = context_model_version.get_artifact(
        lazy_loader.artifact_name, lazy_loader.artifact_version
    )
    if not artifact_:
        raise ValueError(
            error_prefix
            + f"Artifact `{lazy_loader.artifact_name}::{lazy_loader.artifact_version}` "
            f"not found in model `{context_model_version.model.name}` "
            f"version `{context_model_version.name}`."
        )

    if lazy_loader.metadata_name is None:
        return StepRunInputResponse(
            input_type=StepRunInputArtifactType.OVERRIDE
            if overridden
            else StepRunInputArtifactType.LAZY_LOADED,
            **artifact_.model_dump(),
        )

    try:
        return StepRunInputValue(
            value=artifact_.run_metadata[lazy_loader.metadata_name],
            source_type=source.type,
            overridden=overridden,
        )
    except KeyError:
        raise ValueError(
            error_prefix
            + f"Artifact run metadata `{lazy_loader.metadata_name}` "
            "could not be found in artifact "
            f"`{lazy_loader.artifact_name}::{lazy_loader.artifact_version}`."
        )
