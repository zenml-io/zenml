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


def func_namer():
    return "dummy_dynamic_" + str(43)


lambda_namer = lambda: "dummy_dynamic_" + str(42)  # noqa
str_namer = "dummy_dynamic_time_{time}"
static_namer = "dummy_static"


def _validate_name_by_value(name: str, value: str) -> bool:
    if value == "func_namer":
        return name == func_namer()
    if value == "lambda_namer":
        return name == lambda_namer()
    if value == "str_namer":
        return name.startswith("dummy_dynamic_time_")
    if value == "static_namer":
        return name == "dummy_static"
    return False


@step
def dynamic_single_lambda() -> Annotated[str, lambda_namer]:
    return "lambda_namer"


@step
def dynamic_single_callable() -> Annotated[str, func_namer]:
    return "func_namer"


@step
def dynamic_single_string() -> Annotated[str, str_namer]:
    return "str_namer"


@step
def dynamic_tuple() -> (
    Tuple[
        Annotated[str, lambda_namer],
        Annotated[str, func_namer],
        Annotated[str, str_namer],
    ]
):
    return "lambda_namer", "func_namer", "str_namer"


@step
def mixed_tuple() -> (
    Tuple[
        Annotated[str, static_namer],
        Annotated[str, lambda_namer],
        Annotated[str, func_namer],
        Annotated[str, str_namer],
    ]
):
    return "static_namer", "lambda_namer", "func_namer", "str_namer"


@step
def static_single() -> Annotated[str, static_namer]:
    return "static_namer"


@step
def mixed_tuple_artifact_config() -> (
    Tuple[
        Annotated[str, ArtifactConfig(name=static_namer)],
        Annotated[str, ArtifactConfig(name=lambda_namer)],
        Annotated[str, ArtifactConfig(name=func_namer)],
        Annotated[str, ArtifactConfig(name=str_namer)],
    ]
):
    return "static_namer", "lambda_namer", "func_namer", "str_namer"


@pytest.mark.parametrize(
    "step",
    [
        dynamic_single_lambda,
        dynamic_single_callable,
        dynamic_single_string,
        dynamic_tuple,
        mixed_tuple,
        static_single,
        mixed_tuple_artifact_config,
    ],
    ids=[
        "dynamic_single_lambda",
        "dynamic_single_callable",
        "dynamic_single_string",
        "dynamic_tuple",
        "mixed_tuple",
        "static_single",
        "mixed_tuple_artifact_config",
    ],
)
def test_various_naming_scenarios(step: Callable, clean_client: Client):
    @pipeline
    def _inner():
        step()

    p: PipelineRunResponse = _inner()
    for step_response in p.steps.values():
        for k in step_response.outputs.keys():
            value = clean_client.get_artifact_version(k).load()
            assert _validate_name_by_value(k, value)
