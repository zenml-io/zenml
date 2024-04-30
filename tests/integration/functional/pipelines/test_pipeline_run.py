from zenml import pipeline, step


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
