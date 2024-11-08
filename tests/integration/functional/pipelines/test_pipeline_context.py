import pytest
import yaml
from typing_extensions import Annotated

from zenml import (
    Model,
    get_pipeline_context,
    get_step_context,
    log_metadata,
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
    ), "Not accessible inside pipeline"
    assert context.enable_cache is False, "Not accessible inside pipeline"
    assert context.extra == {"foo": "bar"}, "Not accessible inside pipeline"
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
        get_step_context().model.set_stage("production")
    return 1


@step(enable_cache=False)
def asserter_step(i: int):
    assert i == 1


@pipeline(model=Model(name="foo"))
def producer_pipe(do_promote: bool):
    promoter_step(do_promote)


@pipeline(model=Model(name="foo", version="production"))
def consumer_pipe():
    mv = get_pipeline_context().model
    asserter_step(mv.get_artifact("producer_pipe::promoter_step::output"))


def test_that_argument_can_be_a_get_artifact_of_model_in_pipeline_context(
    clean_client: "Client",
):
    producer_pipe(True)
    consumer_pipe()


def test_that_argument_as_get_artifact_of_model_in_pipeline_context_fails_if_not_found(
    clean_client: "Client",
):
    producer_pipe(False)
    with pytest.raises(RuntimeError):
        consumer_pipe()


@step
def producer() -> Annotated[str, "bar"]:
    """Produce artifact with metadata and attach metadata to model version."""
    model = get_step_context().model

    log_metadata(
        metadata={"foobar": "model_meta_" + model.version},
        model_name=model.name,
        model_version=model.version,
    )
    log_metadata(metadata={"foobar": "artifact_meta_" + model.version})
    return "artifact_data_" + model.version


@step
def asserter(artifact: str, artifact_metadata: str, model_metadata: str):
    """Assert that passed in values are loaded in lazy mode.

    They do not exist before actual run of the pipeline.
    """
    ver = get_step_context().model.version
    assert artifact == "artifact_data_" + ver
    assert artifact_metadata == "artifact_meta_" + ver
    assert model_metadata == "model_meta_" + ver


def test_pipeline_context_can_load_model_artifacts_and_metadata_in_lazy_mode(
    clean_client: "Client",
):
    """Tests that user can load model artifacts and metadata in lazy mode in pipeline codes."""

    model_name = "foo"

    @pipeline(model=Model(name=model_name), enable_cache=False)
    def dummy():
        producer()
        model = get_pipeline_context().model
        artifact = model.get_artifact("bar")
        artifact_metadata = artifact.run_metadata["foobar"]
        model_metadata = model.run_metadata["foobar"]
        asserter(
            artifact, artifact_metadata, model_metadata, after=["producer"]
        )

    with pytest.raises(KeyError):
        clean_client.get_model(model_name)
    with pytest.raises(KeyError):
        clean_client.get_artifact_version("bar")
    dummy()
