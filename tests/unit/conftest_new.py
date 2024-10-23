import pytest

from zenml import pipeline, step
from zenml.pipelines.pipeline_definition import Pipeline


@step
def empty_step() -> None:
    return None


@pipeline
def _empty_pipeline() -> None:
    empty_step()


@pytest.fixture
def empty_pipeline() -> Pipeline:
    return _empty_pipeline.copy()
