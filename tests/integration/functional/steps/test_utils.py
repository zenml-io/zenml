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

"""Tests for utility functions and classes to run ZenML steps."""


from zenml import pipeline, step
from zenml.steps.utils import log_step_metadata


@step
def step_metadata_logging_step() -> str:
    """A step that does nothing interesting."""
    return "42"


def test_log_step_metadata_using_latest_run(clean_client):
    """Test logging step metadata for the latest run."""

    @pipeline
    def step_metadata_logging_pipeline():
        step_metadata_logging_step()

    step_metadata_logging_pipeline()
    run_before_log = step_metadata_logging_pipeline.model.last_run
    output_before_log = run_before_log.steps[
        "step_metadata_logging_step"
    ].output
    assert not output_before_log.run_metadata

    step_metadata = {
        "description": "Aria is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_step_metadata(
        metadata=step_metadata,
        step_name="step_metadata_logging_step",
        pipeline_name="step_metadata_logging_pipeline",
    )
    run_after_log = step_metadata_logging_pipeline.model.last_run
    output_after_log = run_after_log.steps["step_metadata_logging_step"].output
    assert "description" in output_after_log.run_metadata
    assert (
        output_after_log.run_metadata["description"].value == "Aria is great!"
    )
    assert "metrics" in output_after_log.run_metadata
    assert output_after_log.run_metadata["metrics"].value == {"accuracy": 0.9}


def test_log_step_metadata_using_specific_params(clean_client):
    """Test logging step metadata for a specific step."""

    @pipeline
    def step_metadata_logging_pipeline():
        step_metadata_logging_step()

    step_metadata_logging_pipeline()
    step_metadata_logging_pipeline()
    run_before_log = step_metadata_logging_pipeline.model.runs[0]
    output_before_log = run_before_log.steps[
        "step_metadata_logging_step"
    ].output
    assert not output_before_log.run_metadata

    step_metadata = {
        "description": "Aria is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_step_metadata(
        metadata=step_metadata,
        step_name="step_metadata_logging_step",
        pipeline_name="step_metadata_logging_pipeline",
    )
    run_after_log = step_metadata_logging_pipeline.model.last_run
    output_after_log = run_after_log.steps["step_metadata_logging_step"].output
    assert "description" in output_after_log.run_metadata
    assert (
        output_after_log.run_metadata["description"].value == "Aria is great!"
    )
    assert "metrics" in output_after_log.run_metadata
    assert output_after_log.run_metadata["metrics"].value == {"accuracy": 0.9}
