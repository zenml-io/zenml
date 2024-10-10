import os
from unittest.mock import patch

from zenml import pipeline, step
from zenml.constants import ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING


@step(enable_cache=False)
def constant_int_output_test_step() -> int:
    return 42


def test_pipeline_run_returns_up_to_date_run_info():
    @pipeline
    def _pipeline():
        constant_int_output_test_step()

    pipeline_run_info = _pipeline()

    assert "constant_int_output_test_step" in pipeline_run_info.steps
    assert (
        pipeline_run_info.steps["constant_int_output_test_step"].status
        == "completed"
    )


@step
def noop() -> None:
    pass


def test_pipeline_run_computes_clientside_cache(clean_client, mocker):
    """Tests that running a pipeline computes the cached steps client-side and
    only forwards the non-cached steps to the orchestrator.
    """
    step_with_cache_enabled = noop.with_options(enable_cache=True)
    step_with_cache_disabled = noop.with_options(enable_cache=False)

    @pipeline
    def partial_cached_pipeline():
        step_with_cache_enabled(id="step_1")
        step_with_cache_enabled(id="step_2", after="step_1")
        step_with_cache_disabled(id="step_3", after="step_1")
        step_with_cache_enabled(id="step_4", after="step_3")

    partial_cached_pipeline()

    mock_prepare_or_run_pipeline = mocker.patch.object(
        clean_client.active_stack.orchestrator, "prepare_or_run_pipeline"
    )
    partial_cached_pipeline()
    assert mock_prepare_or_run_pipeline.call_count == 1

    _, call_kwargs = mock_prepare_or_run_pipeline.call_args
    assert set(call_kwargs["deployment"].step_configurations.keys()) == {
        "step_3",
        "step_4",
    }


def test_fully_cached_pipeline_doesnt_call_orchestrator_implementation(
    clean_client, mocker
):
    """Tests that a fully cached pipeline does not get forwarded to the
    specific orchestrator implementation."""
    step_with_cache_enabled = noop.with_options(enable_cache=True)

    @pipeline
    def full_cached_pipeline():
        step_with_cache_enabled(id="step_1")
        step_with_cache_enabled(id="step_2", after="step_1")

    full_cached_pipeline()

    mock_prepare_or_run_pipeline = mocker.patch.object(
        clean_client.active_stack.orchestrator, "prepare_or_run_pipeline"
    )
    full_cached_pipeline()
    mock_prepare_or_run_pipeline.assert_not_called()


def test_environment_variable_can_be_used_to_disable_clientside_caching(
    clean_client, mocker
):
    """Tests that the environment variable to disable client-side caching
    works.
    """
    step_with_cache_enabled = noop.with_options(enable_cache=True)

    @pipeline
    def full_cached_pipeline():
        step_with_cache_enabled(id="step_1")
        step_with_cache_enabled(id="step_2", after="step_1")

    full_cached_pipeline()

    mock_prepare_or_run_pipeline = mocker.patch.object(
        clean_client.active_stack.orchestrator, "prepare_or_run_pipeline"
    )

    with patch.dict(
        os.environ, {ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING: "True"}
    ):
        full_cached_pipeline()

    mock_prepare_or_run_pipeline.assert_called()
