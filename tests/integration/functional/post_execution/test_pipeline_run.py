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
"""Integration tests for pipeline run post-execution functionality."""
import pytest

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.config.schedule import Schedule
from zenml.environment import get_run_environment_dict
from zenml.post_execution import get_pipeline, get_run, get_unlisted_runs


def test_get_run(clean_client, connected_two_step_pipeline):
    """Test that `get_run()` returns the correct run."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    run_ = get_pipeline("connected_two_step_pipeline").runs[0]
    assert get_run(run_.name) == run_


def test_get_run_fails_for_non_existent_run():
    """Test that `get_run()` raises a `KeyError` for non-existent runs."""
    with pytest.raises(KeyError):
        get_run("non_existent_run")


def test_get_unlisted_runs(clean_client, connected_two_step_pipeline):
    """Test that `get_unlisted_runs()` only returns unlisted runs."""
    assert len(get_unlisted_runs()) == 0
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    assert len(get_unlisted_runs()) == 0
    pipeline_instance.run(unlisted=True)
    assert len(get_unlisted_runs()) == 1


def test_pipeline_run_has_client_and_orchestrator_environment(
    clean_client, connected_two_step_pipeline
):
    """Test that the run has correct client and orchestrator environments."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    test_environment = get_run_environment_dict()
    assert pipeline_run.client_environment == test_environment
    assert pipeline_run.orchestrator_environment == test_environment


def test_scheduled_pipeline_run_has_schedule_id(
    clean_client, connected_two_step_pipeline
):
    """Test that a scheduled pipeline run has a schedule ID."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    schedule = Schedule(cron_expression="*/5 * * * *")
    pipeline_instance.run(schedule=schedule)
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    assert pipeline_run.schedule_id is not None
