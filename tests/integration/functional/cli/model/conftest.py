#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import Annotated, Tuple
from uuid import uuid4

import pytest

from zenml import pipeline, step
from zenml.client import Client
from zenml.model import (
    ArtifactConfig,
    DeploymentArtifactConfig,
    ModelArtifactConfig,
    ModelConfig,
)
from zenml.models import ModelFilterModel

PREFIX = "tests_integration_functional_cli_model_"
NAME = f"{PREFIX}{uuid4()}"


@step
def step_1() -> Annotated[int, NAME + "a", ArtifactConfig()]:
    return 1


@step
def step_2() -> (
    Tuple[
        Annotated[int, NAME + "b", ModelArtifactConfig()],
        Annotated[int, NAME + "c", DeploymentArtifactConfig()],
    ]
):
    return 2, 3


@pipeline(
    model_config=ModelConfig(name=NAME, create_new_model_version=True),
    name=NAME,
)
def pipeline():
    step_1()
    step_2()


@pytest.fixture
def model_watch_tower_data(clean_workspace, connected_two_step_pipeline):
    """Fixture to get a clean workspace with existing model watchtower data."""


def pytest_sessionfinish(session):
    """Clean-up"""
    try:
        run = Client().get_pipeline_run(NAME)
        Client().delete_pipeline_run(NAME)
        for step_run in run.steps.values():
            for output in step_run.outputs.values():
                Client().delete_artifact(output.id)
    except Exception:
        pass
    try:
        Client().delete_pipeline(NAME)
    except Exception:
        pass
    try:
        for each in Client().list_models(
            ModelFilterModel(name=f"contains:{PREFIX}")
        ):
            Client().delete_model(each.id)
    except Exception:
        pass


@pytest.fixture
def clean_workspace_with_models(clean_workspace):
    """Fixture to get a clean workspace with an existing pipeline run in it."""
    pipeline.with_options(run_name=NAME)()
    return clean_workspace
