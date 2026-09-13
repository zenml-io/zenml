"""Tests for the request savings enabled by the execution context."""

import os
from unittest.mock import patch

from zenml import pipeline, step
from zenml.constants import ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING
from zenml.enums import ExecutionStatus
from zenml.orchestrators.step_launcher import StepLauncher


@step(enable_cache=False)
def int_output() -> int:
    return 1


@step(enable_cache=False)
def add_one(value: int) -> int:
    return value + 1


@pipeline
def chain_pipeline():
    add_one(add_one(int_output()))


@pipeline(dynamic=True, enable_cache=False)
def dynamic_chain_pipeline():
    add_one(add_one(int_output()))


@pipeline(dynamic=True, enable_cache=False)
def dynamic_concurrent_pipeline():
    future = int_output.submit()
    add_one.submit(future).result()


def test_static_pipeline_reuses_run_and_step_runs(clean_client, mocker):
    """Tests that a static pipeline run creates the pipeline run once and
    resolves step inputs without additional step run fetches."""
    get_or_create_run_spy = mocker.spy(
        type(clean_client.zen_store), "get_or_create_run"
    )
    list_run_steps_spy = mocker.spy(
        type(clean_client.zen_store), "list_run_steps"
    )
    launch_spy = mocker.spy(StepLauncher, "launch")

    chain_pipeline()

    # One call creates the placeholder run at submission time, one call in the
    # launcher of the first step replaces it. The launchers of the remaining
    # steps reuse the run from the execution context.
    assert get_or_create_run_spy.call_count == 2
    assert list_run_steps_spy.call_count == 0
    assert launch_spy.call_count == 3
    for step_run in launch_spy.spy_return_list:
        assert step_run.status == ExecutionStatus.COMPLETED
        assert step_run.outputs


def test_dynamic_pipeline_reuses_run_and_step_runs(clean_client, mocker):
    """Tests that a dynamic pipeline run reuses the placeholder run and does
    not re-fetch step runs after inline steps finished."""
    get_or_create_run_spy = mocker.spy(
        type(clean_client.zen_store), "get_or_create_run"
    )
    get_run_step_spy = mocker.spy(type(clean_client.zen_store), "get_run_step")

    dynamic_chain_pipeline()

    # The only call creates the placeholder run at submission time. All step
    # launchers reuse the run from the execution context.
    assert get_or_create_run_spy.call_count == 1
    assert get_run_step_spy.call_count == 0


def test_dynamic_concurrent_pipeline_reuses_run_and_step_runs(
    clean_client, mocker
):
    """Tests that a dynamic pipeline run with concurrent inline steps reuses
    the placeholder run and does not re-fetch step runs."""
    get_or_create_run_spy = mocker.spy(
        type(clean_client.zen_store), "get_or_create_run"
    )
    get_run_step_spy = mocker.spy(type(clean_client.zen_store), "get_run_step")

    dynamic_concurrent_pipeline()

    # The only call creates the placeholder run at submission time. All step
    # launchers reuse the run from the execution context.
    assert get_or_create_run_spy.call_count == 1
    assert get_run_step_spy.call_count == 0


def test_environment_variable_disables_execution_context_caching(
    clean_client, mocker
):
    """Tests that the environment variable to disable execution context
    caching works."""
    get_or_create_run_spy = mocker.spy(
        type(clean_client.zen_store), "get_or_create_run"
    )

    with patch.dict(
        os.environ, {ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING: "True"}
    ):
        chain_pipeline()

    # One call creates the placeholder run at submission time, and without the
    # execution context each of the three step launchers calls it again.
    assert get_or_create_run_spy.call_count == 4
