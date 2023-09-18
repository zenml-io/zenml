from zenml import get_step_context, pipeline, step
from zenml.model.model_config import ModelConfig


@step(
    model_config=ModelConfig(name="foo", version="bar"),
)
def _assert_that_model_config_set():
    assert get_step_context().step_run.config.model_config.name == "foo"
    assert get_step_context().step_run.config.model_config.version == "bar"


def test_model_config_passed_to_step_context():
    """Test that model config was passed to step context."""

    @pipeline(name="bar")
    def _simple_step_pipeline():
        _assert_that_model_config_set()

    _simple_step_pipeline()
