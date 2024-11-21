#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

from typing import Callable, Tuple

import pytest
from typing_extensions import Annotated

from zenml import ArtifactConfig, pipeline, step
from zenml.client import Client
from zenml.models.v2.core.pipeline_run import PipelineRunResponse

str_namer_standard = "dummy_dynamic_dt_{date}_{time}"
str_namer_custom = "dummy_dynamic_custom_{funny_name}"
static_namer = "dummy_static"


def _validate_name_by_value(name: str, value: str) -> bool:
    if value == "str_namer_standard":
        return name.startswith("dummy_dynamic_dt_")
    if value == "str_namer_custom":
        return name.startswith("dummy_dynamic_custom_")
    if value == "static_namer":
        return name == "dummy_static"
    return False


@step
def dynamic_single_string_standard() -> Annotated[str, str_namer_standard]:
    return "str_namer_standard"


@step(extra_name_placeholders={"funny_name": "name_placeholder"})
def dynamic_single_string_custom() -> Annotated[str, str_namer_custom]:
    return "str_namer_custom"


@step
def dynamic_single_string_custom_no_default() -> (
    Annotated[str, str_namer_custom]
):
    return "str_namer_custom"


@step(extra_name_placeholders={"funny_name": "name_placeholder"})
def dynamic_tuple() -> (
    Tuple[
        Annotated[str, str_namer_standard],
        Annotated[str, str_namer_custom],
    ]
):
    return "str_namer_standard", "str_namer_custom"


@step(extra_name_placeholders={"funny_name": "name_placeholder"})
def mixed_tuple() -> (
    Tuple[
        Annotated[str, str_namer_standard],
        Annotated[str, static_namer],
        Annotated[str, str_namer_custom],
    ]
):
    return "str_namer_standard", "static_namer", "str_namer_custom"


@step
def static_single() -> Annotated[str, static_namer]:
    return "static_namer"


@step(extra_name_placeholders={"funny_name": "name_placeholder"})
def mixed_tuple_artifact_config() -> (
    Tuple[
        Annotated[str, ArtifactConfig(name=static_namer)],
        Annotated[str, ArtifactConfig(name=str_namer_standard)],
        Annotated[str, ArtifactConfig(name=str_namer_custom)],
    ]
):
    return "static_namer", "str_namer_standard", "str_namer_custom"


@pytest.mark.parametrize(
    "step",
    [
        dynamic_single_string_standard,
        dynamic_single_string_custom,
        dynamic_tuple,
        mixed_tuple,
        static_single,
        mixed_tuple_artifact_config,
    ],
    ids=[
        "dynamic_single_string_standard",
        "dynamic_single_string_custom",
        "dynamic_tuple",
        "mixed_tuple",
        "static_single",
        "mixed_tuple_artifact_config",
    ],
)
def test_various_naming_scenarios(step: Callable, clean_client: Client):
    """Test that dynamic naming works in both normal and cached runs.

    In cached run the names of the dynamic artifacts shall remain same as in real run.
    """

    @pipeline
    def _inner():
        step()

    p1: PipelineRunResponse = _inner.with_options(enable_cache=False)()
    for step_response in p1.steps.values():
        for k in step_response.outputs.keys():
            value = clean_client.get_artifact_version(k).load()
            assert _validate_name_by_value(k, value)

    p2: PipelineRunResponse = _inner.with_options(enable_cache=True)()
    for step_response in p2.steps.values():
        assert set(step_response.outputs.keys()) == set(
            p1.steps[step_response.name].outputs.keys()
        )
        for k in step_response.outputs.keys():
            value = clean_client.get_artifact_version(k).load()
            assert _validate_name_by_value(k, value)


def test_sequential_executions_have_different_names(clean_client: "Client"):
    """Test that dynamic naming works each time for unique uncached runs."""

    @pipeline(enable_cache=False)
    def _inner(name_placeholder: str):
        dynamic_single_string_custom.with_options(
            extra_name_placeholders={"funny_name": name_placeholder}
        )()

    p1: PipelineRunResponse = _inner("funny_name_42")
    p2: PipelineRunResponse = _inner("this_is_not_funny")

    assert set(p1.steps["dynamic_single_string_custom"].outputs.keys()) != set(
        p2.steps["dynamic_single_string_custom"].outputs.keys()
    )


def test_execution_fails_on_custom_but_not_provided_name(
    clean_client: "Client",
):
    """Test that dynamic naming fails on custom placeholder, if they are not provided."""

    @pipeline(enable_cache=False)
    def _inner():
        dynamic_single_string_custom_no_default.with_options(
            extra_name_placeholders={"not_a_funny_name": "it's gonna fail"}
        )()

    with pytest.raises(
        KeyError,
        match="Could not format the name template `dummy_dynamic_custom_{funny_name}`. Missing key: 'funny_name'",
    ):
        _inner()
