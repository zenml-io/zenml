import pytest
import yaml

from zenml import (
    ModelVersion,
    get_pipeline_context,
    get_step_context,
    pipeline,
    step,
)
from zenml.client import Client


@step
def assert_pipeline_context_in_step():
    with pytest.raises(RuntimeError, match="Inside a step"):
        get_pipeline_context()

    context = get_step_context()
    assert (
        context.pipeline.name == "assert_pipeline_context_in_pipeline"
    ), "Not accessible inside running step"
    assert (
        context.pipeline_run.config.enable_cache is False
    ), "Not accessible inside running step"
    assert context.pipeline_run.config.extra == {
        "foo": "bar"
    }, "Not accessible inside running step"


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


def test_pipeline_context_available_as_config_yaml(tmp_path):
    """Tests that the pipeline context is available as a config yaml."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"extra": {"foo": "bar"}}))

    assert_pipeline_context_in_pipeline.with_options(
        config_path=str(config_path)
    )


@step(enable_cache=False)
def promoter_step(do_promote: bool) -> int:
    if do_promote:
        get_step_context().model_version.set_stage("production")
    return 1


@step(enable_cache=False)
def asserter_step(i: int):
    assert i == 1


@pipeline(model_version=ModelVersion(name="foo"))
def producer_pipe(do_promote: bool):
    promoter_step(do_promote)


@pipeline(model_version=ModelVersion(name="foo", version="production"))
def consumer_pipe():
    mv = get_pipeline_context().model_version
    asserter_step(
        mv.get_artifact(
            "producer_pipe::promoter_step::output", as_external_artifact=True
        )
    )


def test_that_argument_can_be_a_get_artifact_of_model_version_in_pipeline_context(
    clean_client: "Client",
):
    producer_pipe(True)
    consumer_pipe()


def test_that_argument_as_get_artifact_of_model_version_in_pipeline_context_fails_if_not_found(
    clean_client: "Client",
):
    producer_pipe(False)
    with pytest.raises(RuntimeError):
        consumer_pipe()
