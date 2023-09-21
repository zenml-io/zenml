from zenml import get_step_context, pipeline, step
from zenml.model.model_config import ModelConfig


@step
def _assert_that_model_config_set(name="foo", version="bar"):
    """Step asserting that passed model name and version is in model context."""
    assert get_step_context().model_config.name == name
    assert get_step_context().model_config.version == version


def test_model_config_passed_to_step_context_via_step():
    """Test that model config was passed to step context via step."""

    @pipeline(name="bar")
    def _simple_step_pipeline():
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(name="foo", version="bar"),
        )()

    _simple_step_pipeline()


def test_model_config_passed_to_step_context_via_pipeline():
    """Test that model config was passed to step context via pipeline."""

    @pipeline(name="bar", model_config=ModelConfig(name="foo", version="bar"))
    def _simple_step_pipeline():
        _assert_that_model_config_set()

    _simple_step_pipeline()


def test_model_config_passed_to_step_context_via_step_and_pipeline():
    """Test that model config was passed to step context via both, but step is dominating."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", version="foo"),
    )
    def _simple_step_pipeline():
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(name="foo", version="bar"),
        )()

    _simple_step_pipeline()


def test_model_config_passed_to_step_context_and_switches():
    """Test that model config was passed to step context via both and switches possible."""

    @pipeline(
        name="bar",
        model_config=ModelConfig(name="bar", version="foo"),
    )
    def _simple_step_pipeline():
        # this step will use ModelConfig from itself
        _assert_that_model_config_set.with_options(
            model_config=ModelConfig(name="foo", version="bar"),
        )()
        # this step will use ModelConfig from pipeline
        _assert_that_model_config_set(name="bar", version="foo")

    _simple_step_pipeline()
