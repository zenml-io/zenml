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
"""Integration tests for pipeline models."""

from typing import TYPE_CHECKING

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
    int_plus_two_test_step,
)

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


def test_pipeline_run_linkage(connected_two_step_pipeline):
    """Integration test for `pipeline.get_runs()` and related properties."""
    pipeline_instance: BasePipeline = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    for i in range(3):
        pipeline_instance.run()
        model = pipeline_instance.model
        runs = model.get_runs()
        assert len(runs) == model.num_runs == i + 1
        assert runs == model.runs
        assert runs[0] == model.last_run == model.last_successful_run

    assert pipeline_instance.model.num_runs == 3

    # Check different versions of the pipeline are using the same model
    pipeline_instance_2: BasePipeline = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_two_test_step(),
    )
    pipeline_instance_2.run()
    assert pipeline_instance.model.num_runs == 4
    assert pipeline_instance_2.model.num_runs == 4
    pipeline_instance.run()
    assert pipeline_instance.model.num_runs == 5
    assert pipeline_instance_2.model.num_runs == 5
    pipeline_instance_2.run()
    assert pipeline_instance.model.num_runs == 6
    assert pipeline_instance_2.model.num_runs == 6
