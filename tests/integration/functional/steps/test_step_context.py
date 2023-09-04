import json
import os
from typing import Optional, Type

from pydantic import BaseModel

from zenml import get_step_context, pipeline, step
from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class ComplexObject(BaseModel):
    """This is a custom object to be materialized with ComplexObjectMaterializer."""

    name: str
    pipeline_name: Optional[str]


class ComplexObjectMaterializer(BaseMaterializer):
    """This materializer just tries to access step context inside save."""

    ASSOCIATED_TYPES = (ComplexObject,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.STATISTICS

    def load(self, data_type: Type[ComplexObject]) -> ComplexObject:
        super().load(data_type)

        with fileio.open(os.path.join(self.uri, "data.json"), "r") as f:
            data_json = json.loads(f.read())

        return ComplexObject(**data_json)

    def save(self, data: ComplexObject) -> None:
        super().save(data)

        # here we need access to the step context
        data.pipeline_name = get_step_context().pipeline.name
        with fileio.open(os.path.join(self.uri, "data.json"), "w") as f:
            f.write(data.json())


@step(
    output_materializers=[
        ComplexObjectMaterializer,
    ]
)
def _output_complex_object_step():
    """This step would call `save` of `ComplexObjectMaterializer`.
    `save` should not fail and have access to the step context"""
    return ComplexObject(name="foo")


@step
def _input_complex_object_step(inp: ComplexObject):
    """This step would call `load` of `ComplexObjectMaterializer`.
    `load` should be able to read detail of step context created on `save`."""
    assert inp.pipeline_name == get_step_context().pipeline.name


@step
def _access_step_context_step():
    """This step tries to access step context while inside Step execution"""
    assert get_step_context().pipeline.name == "bar"


def test_materializer_can_access_step_context():
    """Call steps using `ComplexObjectMaterializer` to validate that
    step context is available to Materializers"""

    @pipeline(name="bar")
    def _complex_object_materialization_pipeline():
        complex_object = _output_complex_object_step()
        _input_complex_object_step(complex_object)

    _complex_object_materialization_pipeline()


def test_step_can_access_step_context():
    """Call step using step context directly, before Materializers"""

    @pipeline(name="bar")
    def _simple_step_pipeline():
        _access_step_context_step()

    _simple_step_pipeline()
