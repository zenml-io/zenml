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

from typing import TYPE_CHECKING, Tuple
from unittest.mock import patch
from uuid import uuid4

import pytest
from typing_extensions import Annotated

from tests.integration.functional.zen_stores.utils import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml import pipeline, step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.config.schedule import Schedule
from zenml.enums import ArtifactType
from zenml.model.model import Model

if TYPE_CHECKING:
    from zenml.client import Client


@pytest.fixture(scope="session", autouse=True)
def initialize_store():
    """Fixture to initialize the zen and secrets stores.

    NOTE: this fixture initializes the Zen store and the secrets store
    before any CLI tests are run because some backends (AWS) are known to mess
    up the stdout and stderr streams upon initialization and this impacts the
    click.testing.CliRunner ability to capture the output and restore the
    streams upon exit.
    """
    from zenml.client import Client

    _ = Client().zen_store


@pytest.fixture
def clean_client_with_run(clean_client, connected_two_step_pipeline):
    """Fixture to get a clean workspace with an existing pipeline run in it."""
    connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )()
    return clean_client


@pytest.fixture
def clean_client_with_scheduled_run(
    clean_client: "Client", connected_two_step_pipeline
):
    """Fixture to get a clean workspace with an existing scheduled run in it."""
    schedule = Schedule(cron_expression="*/5 * * * *")

    with patch(
        "zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig.is_schedulable",
        new_callable=lambda: True,
    ):
        connected_two_step_pipeline(
            step_1=constant_int_output_test_step,
            step_2=int_plus_one_test_step,
        ).with_options(schedule=schedule)()
    return clean_client


PREFIX = "tests_integration_functional_cli_model_"
NAME = f"{PREFIX}{uuid4()}"


@step
def step_1() -> Annotated[int, NAME + "a"]:
    return 1


@step
def step_2() -> (
    Tuple[
        Annotated[
            int,
            ArtifactConfig(name=NAME + "b", artifact_type=ArtifactType.MODEL),
        ],
        Annotated[
            int,
            ArtifactConfig(
                name=NAME + "c", artifact_type=ArtifactType.SERVICE
            ),
        ],
    ]
):
    return 2, 3


@pipeline(
    model=Model(name=NAME),
    name=NAME,
)
def pipeline_():
    step_1()
    step_2()


@pytest.fixture
def clean_client_with_models(clean_client: "Client"):
    """Fixture to get a clean workspace with an existing pipeline run in it."""
    pipeline_.with_options(run_name=NAME)()
    return clean_client
