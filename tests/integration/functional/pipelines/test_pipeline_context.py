import pytest

from zenml import get_pipeline_context, pipeline, step


@step
def assert_pipeline_context_in_step():
    with pytest.raises(RuntimeError, match="Inside a step"):
        get_pipeline_context()


@pipeline(enable_cache=False)
def assert_pipeline_context_in_pipeline():
    context = get_pipeline_context()
    assert (
        context.name == "assert_pipeline_context_in_pipeline"
    ), "Not accessible inside composition of pipeline"
    assert (
        context.enable_cache is False
    ), "Not accessible inside composition of pipeline"
    assert context.extra == {
        "foo": "bar"
    }, "Not accessible inside composition of pipeline"
    assert_pipeline_context_in_step()


def test_pipeline_context():
    """Tests the pipeline context accessibility on different stages."""
    with pytest.raises(RuntimeError, match="No active"):
        get_pipeline_context()

    assert_pipeline_context_in_pipeline.with_options(extra={"foo": "bar"})()
