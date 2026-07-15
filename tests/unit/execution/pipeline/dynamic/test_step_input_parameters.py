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
"""Tests for the classification of dynamic step inputs."""

from typing import Any, Dict, Set, Tuple

import pytest

from zenml import ExternalArtifact, pipeline, step
from zenml.config.step_configurations import ArtifactVersionInputSource
from zenml.constants import ENV_ZENML_PARAMETER_SIZE_THRESHOLD
from zenml.models import PipelineRunResponse


class _NotSerializable:
    """Value that can not be passed as a step parameter."""


@step
def _consumer(a: int, b: Dict[str, str], c: Any) -> None:
    pass


@step
def _consumer_with_default(a: int, b: str = "default") -> None:
    assert b == "default"


@step
def _string_consumer(a: str) -> None:
    pass


def _classified_inputs(
    run: PipelineRunResponse, step_name: str
) -> Tuple[Dict[str, Any], Set[str]]:
    """Get the parameters and uploaded inputs of a step.

    Args:
        run: The finished pipeline run.
        step_name: The name of the step.

    Returns:
        The step parameters and the names of the uploaded step inputs.
    """
    step_run = next(
        step_run
        for name, step_run in run.steps.items()
        if name.startswith(step_name)
    )

    return (
        dict(step_run.config.parameters),
        {
            name
            for name, source in step_run.config.inputs.items()
            if isinstance(source, ArtifactVersionInputSource)
        },
    )


@pipeline(dynamic=True, enable_cache=False)
def _plain_inputs_pipeline() -> None:
    _consumer(1, {"k": "v"}, _NotSerializable())


@pipeline(dynamic=True, enable_cache=False)
def _external_artifact_pipeline() -> None:
    _consumer(ExternalArtifact(value=1), {"k": "v"}, _NotSerializable())


@pipeline(dynamic=True, enable_cache=False)
def _default_parameter_pipeline() -> None:
    _consumer_with_default(1)


@pipeline(dynamic=True, enable_cache=False)
def _sized_parameter_pipeline(size: int) -> None:
    _string_consumer("x" * size)


def test_raw_inputs_are_uploaded_by_default() -> None:
    """Raw inputs are uploaded as external artifacts unless opted out."""
    parameters, uploaded = _classified_inputs(
        _plain_inputs_pipeline(), "_consumer"
    )

    assert parameters == {}
    assert uploaded == {"a", "b", "c"}


def test_zero_threshold_uploads_raw_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit zero threshold behaves like the unset default."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "0")

    parameters, uploaded = _classified_inputs(
        _plain_inputs_pipeline(), "_consumer"
    )

    assert parameters == {}
    assert uploaded == {"a", "b", "c"}


def test_negative_threshold_passes_serializable_inputs_as_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A negative threshold parameterizes without a size check."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "-1")

    parameters, uploaded = _classified_inputs(
        _plain_inputs_pipeline(), "_consumer"
    )

    assert parameters == {"a": 1, "b": {"k": "v"}}
    assert uploaded == {"c"}


def test_negative_threshold_ignores_the_input_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A negative threshold parameterizes inputs of any size."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "-1")

    parameters, uploaded = _classified_inputs(
        _sized_parameter_pipeline(size=5000), "_string_consumer"
    )

    assert parameters == {"a": "x" * 5000}
    assert uploaded == set()


def test_input_below_the_threshold_is_a_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An input within the size threshold is passed as a parameter."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "1000")

    parameters, uploaded = _classified_inputs(
        _sized_parameter_pipeline(size=100), "_string_consumer"
    )

    assert parameters == {"a": "x" * 100}
    assert uploaded == set()


def test_input_above_the_threshold_is_uploaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An input above the size threshold falls back to an upload."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "1000")

    parameters, uploaded = _classified_inputs(
        _sized_parameter_pipeline(size=5000), "_string_consumer"
    )

    assert parameters == {}
    assert uploaded == {"a"}


def test_unserializable_inputs_are_uploaded_despite_the_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inputs that can not be parameters keep getting uploaded."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "-1")

    _, uploaded = _classified_inputs(_plain_inputs_pipeline(), "_consumer")

    assert "c" in uploaded


def test_external_artifact_is_uploaded_despite_the_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ExternalArtifact(...)` keeps uploading a serializable input."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "-1")

    parameters, uploaded = _classified_inputs(
        _external_artifact_pipeline(), "_consumer"
    )

    assert parameters == {"b": {"k": "v"}}
    assert uploaded == {"a", "c"}


def test_signature_defaults_still_apply_with_the_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inputs that are not passed keep resolving to their signature default."""
    monkeypatch.setenv(ENV_ZENML_PARAMETER_SIZE_THRESHOLD, "-1")

    parameters, uploaded = _classified_inputs(
        _default_parameter_pipeline(), "_consumer_with_default"
    )

    assert parameters == {"a": 1, "b": "default"}
    assert uploaded == set()
