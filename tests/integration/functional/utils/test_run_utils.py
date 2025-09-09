#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Integration tests for run utils."""

import pytest

from zenml import get_step_context, pipeline, step
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.zen_stores.schemas.pipeline_run_schemas import (
    build_dag,
    find_all_downstream_steps,
)


@step
def step_1() -> str:
    """Step 1 - runs first and succeeds."""
    return "step_1_output"


@step
def step_2(input_from_1: str, should_fail: bool = False) -> str:
    """Step 2 - depends on step 1, will fail in some tests."""
    if should_fail:
        raise RuntimeError("Step 2 intentionally failed")
    return "step_2_output"


@step
def step_3(input_from_1: str) -> str:
    """Step 3 - depends on step 1, runs on the same level as step 2 and 4."""
    return "step_3_output"


@step
def step_4(input_from_1: str) -> str:
    """Step 4 - depends on step 1, runs on the same level as step 2 and 3."""
    return "step_4_output"


@step
def step_5(input_from_2: str) -> str:
    """Step 5 - depends on step 2."""
    return "step_5_output"


@step
def step_6(input_from_3: str) -> str:
    """Step 6 - depends on step 3."""
    return "step_6_output"


@step
def step_7(input_from_4: str) -> str:
    """Step 7 - depends on step 4."""
    context = get_step_context()
    assert context.pipeline_run.in_progress is True
    return "step_7_output"


@step
def step_8(input_from_5: str, input_from_6: str, input_from_7: str) -> str:
    """Step 8 - depends on step 5, 6, 7."""
    return "step_8_output"


@pipeline(enable_cache=False)
def execution_mode_pipeline(fail_step_2: bool = False) -> None:
    """Test pipeline to demonstrate DAG structure for run utils testing.

    Dependency structure:
    - Step 1 → Steps 2, 3, 4
    - Step 2 → Step 5
    - Step 3 → Step 6
    - Step 4 → Step 7
    - Step 5, 6, 7 → Step 8
    """
    output_1 = step_1()

    # These three steps run after step 1
    output_2 = step_2(output_1, should_fail=fail_step_2)
    output_3 = step_3(output_1)
    output_4 = step_4(output_1)

    # These steps depend on the steps above
    output_5 = step_5(output_2)
    output_6 = step_6(output_3)
    output_7 = step_7(output_4)

    # Final step
    _ = step_8(output_5, output_6, output_7)


def test_build_dag(clean_client):
    """Test build_dag with real pipeline execution."""
    # Run the pipeline
    run = execution_mode_pipeline()

    assert run.in_progress is False

    # Get the deployment and extract steps
    deployment = clean_client.get_deployment(run.deployment_id)

    steps = {}
    for step_spec in deployment.pipeline_spec.steps:
        steps[step_spec.pipeline_parameter_name] = step_spec.upstream_steps

    # Build the DAG using our function
    dag = build_dag(steps)

    # Expected DAG structure based on our pipeline
    expected_structure = {
        "step_1": {"step_2", "step_3", "step_4"},
        "step_2": {"step_5"},
        "step_3": {"step_6"},
        "step_4": {"step_7"},
        "step_5": {"step_8"},
        "step_6": {"step_8"},
        "step_7": {"step_8"},
        "step_8": set(),
    }

    assert dag == expected_structure


def test_find_all_downstream_steps(clean_client):
    """Test find_all_downstream_steps with real pipeline structure."""
    # Run the pipeline
    run = execution_mode_pipeline()

    # Get the deployment and extract steps
    deployment = clean_client.get_deployment(run.deployment_id)

    steps = {}
    for step_spec in deployment.pipeline_spec.steps:
        steps[step_spec.pipeline_parameter_name] = step_spec.upstream_steps

    # Build the DAG
    dag = build_dag(steps)

    # Test finding downstream steps from step_1 (should include all others)
    downstream_from_step1 = find_all_downstream_steps("step_1", dag)
    expected_from_step1 = {
        "step_2",
        "step_3",
        "step_4",
        "step_5",
        "step_6",
        "step_7",
        "step_8",
    }
    assert downstream_from_step1 == expected_from_step1

    # Test finding downstream steps from step_3
    downstream_from_step3 = find_all_downstream_steps("step_3", dag)
    expected_from_step3 = {"step_6", "step_8"}
    assert downstream_from_step3 == expected_from_step3

    # Test finding downstream steps from step_2
    downstream_from_step2 = find_all_downstream_steps("step_2", dag)
    expected_from_step2 = {"step_5", "step_8"}
    assert downstream_from_step2 == expected_from_step2

    # Test finding downstream steps from terminal step
    downstream_from_step5 = find_all_downstream_steps("step_8", dag)
    assert downstream_from_step5 == set()


def test_dag_with_failed_step(clean_client):
    """Test DAG functions when some steps fail."""
    with pytest.raises(RuntimeError):
        _ = execution_mode_pipeline(fail_step_2=True)

    run = clean_client.list_pipeline_runs(size=1).items[0]

    # Get the deployment and extract steps
    deployment = clean_client.get_deployment(run.deployment_id)

    steps = {}
    for step_spec in deployment.pipeline_spec.steps:
        steps[step_spec.pipeline_parameter_name] = step_spec.upstream_steps

    # Build the DAG
    dag = build_dag(steps)

    # If step_2 fails, we can still find its downstream dependencies
    downstream_from_failed_step2 = find_all_downstream_steps("step_2", dag)
    assert downstream_from_failed_step2 == {"step_5", "step_8"}

    # Other paths should be unaffected
    downstream_from_step3 = find_all_downstream_steps("step_3", dag)
    assert downstream_from_step3 == {"step_6", "step_8"}


def test_execution_mode_fail_fast(clean_client):
    """Test FAIL_FAST execution mode."""
    # Configure pipeline with FAIL_FAST mode
    pipeline_with_failure = execution_mode_pipeline.with_options(
        execution_mode=ExecutionMode.FAIL_FAST
    )

    with pytest.raises(RuntimeError):
        _ = pipeline_with_failure(fail_step_2=True)

    run = clean_client.list_pipeline_runs(size=1).items[0]

    # Check which steps actually ran
    assert run.status == ExecutionStatus.FAILED
    assert run.steps["step_1"].status == ExecutionStatus.COMPLETED
    assert run.steps["step_2"].status == ExecutionStatus.FAILED
    assert "step_8" not in run.steps


def test_execution_mode_stop_on_failure(clean_client):
    """Test STOP_ON_FAILURE execution mode."""
    pipeline_with_failure = execution_mode_pipeline.with_options(
        execution_mode=ExecutionMode.STOP_ON_FAILURE
    )

    with pytest.raises(RuntimeError):
        _ = pipeline_with_failure(fail_step_2=True)

    run = clean_client.list_pipeline_runs(size=1).items[0]

    assert run.steps["step_1"].status == ExecutionStatus.COMPLETED
    assert run.steps["step_2"].status == ExecutionStatus.FAILED
    assert "step_5" not in run.steps
    assert "step_8" not in run.steps


def test_execution_mode_continue_on_failure(clean_client):
    """Test CONTINUE_ON_FAILURE execution mode."""
    pipeline_with_failure = execution_mode_pipeline.with_options(
        execution_mode=ExecutionMode.CONTINUE_ON_FAILURE
    )

    with pytest.raises(RuntimeError):
        _ = pipeline_with_failure(fail_step_2=True)

    run = clean_client.list_pipeline_runs(size=1).items[0]

    # Check which steps actually ran
    assert run.steps["step_1"].status == ExecutionStatus.COMPLETED
    assert run.steps["step_2"].status == ExecutionStatus.FAILED
    assert run.steps["step_3"].status == ExecutionStatus.COMPLETED
    assert run.steps["step_4"].status == ExecutionStatus.COMPLETED
    assert run.steps["step_6"].status == ExecutionStatus.COMPLETED
    # Step 7 is critical because it checks whether the
    # in progress flag was set correctly, even though step 2 failed.
    assert run.steps["step_7"].status == ExecutionStatus.COMPLETED
    assert "step_5" not in run.steps
    assert "step_8" not in run.steps
