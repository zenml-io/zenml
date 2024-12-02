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

from contextlib import ExitStack as does_not_raise
from typing import Callable, Tuple

import pytest
from typing_extensions import Annotated

from zenml import ArtifactConfig, pipeline, step
from zenml.client import Client
from zenml.models.v2.core.pipeline_run import PipelineRunResponse

str_namer_standard = "dummy_dynamic_dt_{date}_{time}"
str_namer_custom = "dummy_dynamic_custom_{funny_name}"
str_namer_custom_2 = "dummy_dynamic_custom_{funnier_name}"
static_namer = "dummy_static"


def _validate_name_by_value(name: str, value: str) -> bool:
    if value == "str_namer_standard":
        return name.startswith("dummy_dynamic_dt_")
    if value == "str_namer_custom":
        return name.startswith("dummy_dynamic_custom_")
    if value == "static_namer":
        return name == "dummy_static"
    if value == "unannotated":
        return name.startswith("output")
    return False


@step
def dynamic_single_string_standard() -> Annotated[str, str_namer_standard]:
    return "str_namer_standard"


@step(substitutions={"funny_name": "name_placeholder"})
def dynamic_single_string_custom() -> Annotated[str, str_namer_custom]:
    return "str_namer_custom"


@step(substitutions={"funnier_name": "name_placeholder"})
def dynamic_single_string_custom_2() -> Annotated[str, str_namer_custom_2]:
    return "str_namer_custom"


@step
def dynamic_single_string_custom_no_default() -> (
    Annotated[str, str_namer_custom]
):
    return "str_namer_custom"


@step(substitutions={"funny_name": "name_placeholder"})
def dynamic_tuple() -> (
    Tuple[
        Annotated[str, str_namer_standard],
        Annotated[str, str_namer_custom],
    ]
):
    return "str_namer_standard", "str_namer_custom"


@step(substitutions={"funny_name": "name_placeholder"})
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


@step(substitutions={"funny_name": "name_placeholder"})
def mixed_tuple_artifact_config() -> (
    Tuple[
        Annotated[str, ArtifactConfig(name=static_namer)],
        Annotated[str, ArtifactConfig(name=str_namer_standard)],
        Annotated[str, ArtifactConfig(name=str_namer_custom)],
    ]
):
    return "static_namer", "str_namer_standard", "str_namer_custom"


@step
def dynamic_single_string_standard_controlled_return(
    s: str,
) -> Annotated[str, str_namer_standard]:
    return s


@step(substitutions={"funny_name": "name_placeholder"})
def mixed_with_unannotated_returns() -> (
    Tuple[
        Annotated[str, str_namer_standard],
        str,
        Annotated[str, str_namer_custom],
        str,
    ]
):
    return (
        "str_namer_standard",
        "unannotated",
        "str_namer_custom",
        "unannotated",
    )


@step
def step_with_string_input(input_: str) -> None:
    pass


@pytest.mark.parametrize(
    "step",
    [
        dynamic_single_string_standard,
        dynamic_single_string_custom,
        dynamic_tuple,
        mixed_tuple,
        static_single,
        mixed_tuple_artifact_config,
        mixed_with_unannotated_returns,
    ],
    ids=[
        "dynamic_single_string_standard",
        "dynamic_single_string_custom",
        "dynamic_tuple",
        "mixed_tuple",
        "static_single",
        "mixed_tuple_artifact_config",
        "mixed_with_unannotated_returns",
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
            if k.startswith("output"):
                value = clean_client.get_artifact_version(
                    f"{p1.pipeline.name}::{step_response.name}::{k}"
                ).load()
            else:
                value = clean_client.get_artifact_version(k).load()
            assert _validate_name_by_value(k, value)

    p2: PipelineRunResponse = _inner.with_options(enable_cache=True)()
    for step_response in p2.steps.values():
        assert set(step_response.outputs.keys()) == set(
            p1.steps[step_response.name].outputs.keys()
        )
        for k in step_response.outputs.keys():
            if k.startswith("output"):
                value = clean_client.get_artifact_version(
                    f"{p2.pipeline.name}::{step_response.name}::{k}"
                ).load()
            else:
                value = clean_client.get_artifact_version(k).load()
            assert _validate_name_by_value(k, value)


def test_sequential_executions_have_different_names(clean_client: "Client"):
    """Test that dynamic naming works each time for unique uncached runs."""

    @pipeline(enable_cache=False)
    def _inner(name_placeholder: str):
        dynamic_single_string_custom.with_options(
            substitutions={"funny_name": name_placeholder}
        )()

    p1: PipelineRunResponse = _inner("funny_name_42")
    p2: PipelineRunResponse = _inner("this_is_not_funny")

    assert set(p1.steps["dynamic_single_string_custom"].outputs.keys()) != set(
        p2.steps["dynamic_single_string_custom"].outputs.keys()
    )


def test_sequential_executions_have_different_names_in_pipeline_context(
    clean_client: "Client",
):
    """Test that dynamic naming works each time for unique uncached runs."""

    @pipeline(enable_cache=False)
    def _inner():
        dynamic_single_string_custom_no_default()

    @pipeline(enable_cache=False, substitutions={"funny_name": "p_d"})
    def _inner_2():
        dynamic_single_string_custom_no_default()

    @pipeline(enable_cache=False, substitutions={"funny_name": "p_d"})
    def _inner_3():
        dynamic_single_string_custom_no_default.with_options(
            substitutions={"funny_name": "s_wo"}
        )()

    @pipeline(enable_cache=False, substitutions={"funny_name": "p_d"})
    def _inner_4():
        dynamic_single_string_custom()

    p1: PipelineRunResponse = _inner.with_options(
        substitutions={"funny_name": "p_wo"}
    )()
    p2: PipelineRunResponse = _inner_2()
    p3: PipelineRunResponse = _inner_3()
    p4: PipelineRunResponse = _inner_4()
    p5: PipelineRunResponse = _inner_2.with_options(
        substitutions={"funny_name": "p_wo"}
    )()

    assert (
        set(p1.steps["dynamic_single_string_custom_no_default"].outputs.keys())
        != set(
            p2.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )
        != set(
            p3.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )
        != set(p4.steps["dynamic_single_string_custom"].outputs.keys())
    )
    # only pipeline `with_options` -> pipeline with_options
    assert (
        list(
            p1.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )[0]
        == "dummy_dynamic_custom_p_wo"
    )
    # only pipeline deco -> pipeline deco
    assert (
        list(
            p2.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )[0]
        == "dummy_dynamic_custom_p_d"
    )
    # pipeline deco + step with_options -> step with_options
    assert (
        list(
            p3.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )[0]
        == "dummy_dynamic_custom_s_wo"
    )
    # pipeline deco + step deco -> step deco
    assert (
        list(p4.steps["dynamic_single_string_custom"].outputs.keys())[0]
        == "dummy_dynamic_custom_name_placeholder"
    )
    # pipeline deco + with_options -> pipeline with_options
    assert (
        list(
            p5.steps["dynamic_single_string_custom_no_default"].outputs.keys()
        )[0]
        == "dummy_dynamic_custom_p_wo"
    )


def test_execution_fails_on_custom_but_not_provided_name(
    clean_client: "Client",
):
    """Test that dynamic naming fails on custom placeholder, if they are not provided."""

    @pipeline(enable_cache=False)
    def _inner():
        dynamic_single_string_custom_no_default.with_options(
            substitutions={"not_a_funny_name": "it's gonna fail"}
        )()

    with pytest.raises(
        KeyError,
        match="Could not format the name template `dummy_dynamic_custom_{funny_name}`. Missing key: 'funny_name'",
    ):
        _inner()


def test_stored_info_not_affected_by_dynamic_naming(clean_client: "Client"):
    """Test that dynamic naming does not affect stored info."""

    @pipeline(enable_cache=False)
    def _inner(ret: str):
        dynamic_single_string_standard_controlled_return(ret)

    p1: PipelineRunResponse = _inner("output_1")
    p2: PipelineRunResponse = _inner("output_2")

    a1 = clean_client.get_artifact_version(
        list(
            p1.steps[
                "dynamic_single_string_standard_controlled_return"
            ].outputs.keys()
        )[0]
    ).load()
    a2 = clean_client.get_artifact_version(
        list(
            p2.steps[
                "dynamic_single_string_standard_controlled_return"
            ].outputs.keys()
        )[0]
    ).load()
    assert a1 == "output_1" != a2
    assert a2 == "output_2" != a1


def test_that_overrides_work_as_expected(clean_client: "Client"):
    """Test that dynamic naming does not affect stored info."""

    @pipeline(
        enable_cache=False, substitutions={"date": "not_a_date_actually"}
    )
    def _inner(pass_to_step: str = ""):
        if pass_to_step:
            dynamic_single_string_custom_no_default.with_options(
                substitutions={
                    "funny_name": pass_to_step,
                    "date": pass_to_step,
                }
            )()
        else:
            dynamic_single_string_custom_no_default()

    p1: PipelineRunResponse = _inner.with_options(
        substitutions={"funny_name": "pipeline_level"}
    )()
    p2: PipelineRunResponse = _inner("step_level")
    p1_subs = p1.config.substitutions
    p2_subs = p2.config.substitutions

    assert p1_subs["date"] == "not_a_date_actually"
    assert p2_subs["date"] == "not_a_date_actually"
    assert p1_subs["time"] != p2_subs["time"]
    assert p1_subs["funny_name"] == "pipeline_level"
    assert "funny_name" not in p2_subs

    p1_step_subs = p1.steps[
        "dynamic_single_string_custom_no_default"
    ].config.substitutions
    p2_step_subs = p2.steps[
        "dynamic_single_string_custom_no_default"
    ].config.substitutions
    assert p1_step_subs["time"] != p2_step_subs["time"]
    assert p1_step_subs["date"] != p2_step_subs["date"]
    assert p1_step_subs["date"] == "not_a_date_actually"
    assert p2_step_subs["date"] == "step_level"
    assert p1_step_subs["funny_name"] == "pipeline_level"
    assert p2_step_subs["funny_name"] == "step_level"


def test_dynamically_named_artifacts_in_downstream_steps(
    clean_client: "Client",
):
    """Test that dynamically named artifacts can be used in downstream steps."""

    @pipeline(enable_cache=False)
    def _inner(ret: str):
        artifact = dynamic_single_string_standard()
        step_with_string_input(artifact)

    with does_not_raise():
        _inner("output_1")
