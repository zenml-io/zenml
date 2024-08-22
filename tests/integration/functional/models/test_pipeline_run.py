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
"""Integration tests for pipeline run models."""

from typing import TYPE_CHECKING

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.config.schedule import Schedule
from zenml.environment import get_run_environment_dict

if TYPE_CHECKING:
    from zenml.client import Client


def test_pipeline_run_artifacts(
    clean_client: "Client", connected_two_step_pipeline
):
    """Integration test for `run.artifacts` property."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )

    # Non-cached run created two artifacts, one per step
    pipeline_instance()
    assert len(pipeline_instance.model.last_run.artifact_versions) == 2
    assert (
        len(pipeline_instance.model.last_run.produced_artifact_versions) == 2
    )

    # Cached run did not produce any artifacts
    pipeline_instance()
    assert len(pipeline_instance.model.last_run.artifact_versions) == 2
    assert (
        len(pipeline_instance.model.last_run.produced_artifact_versions) == 0
    )


def test_pipeline_run_has_client_and_orchestrator_environment(
    clean_client: "Client", connected_two_step_pipeline
):
    """Test that the run has correct client and orchestrator environments."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    test_environment = get_run_environment_dict()
    assert pipeline_run.client_environment == test_environment
    assert pipeline_run.orchestrator_environment == test_environment


def test_scheduled_pipeline_run_has_schedule_id(
    clean_client: "Client", connected_two_step_pipeline
):
    """Test that a scheduled pipeline run has a schedule ID."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    schedule = Schedule(cron_expression="*/5 * * * *")
    pipeline_instance.with_options(schedule=schedule)()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    assert pipeline_run.schedule is not None
