import json
import os
from typing import Any, Dict, List, Optional, Tuple, Type

import pytest
from pydantic import BaseModel
from typing_extensions import Annotated

from zenml import get_step_context, log_artifact_metadata, pipeline, step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class ComplexObject(BaseModel):
    """This is a custom object to be materialized with ComplexObjectMaterializer."""

    name: str
    pipeline_name: Optional[str] = None


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
            f.write(data.model_dump_json())


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


@step
def output_metadata_logging_step() -> Annotated[int, "my_output"]:
    log_artifact_metadata(metadata={"some_key": "some_value"})
    return 42


@step
def step_context_metadata_reader_step(my_input: int) -> None:
    step_context = get_step_context()
    my_input_metadata = step_context.inputs["my_input"].run_metadata
    assert my_input_metadata["some_key"].value == "some_value"


def test_input_artifacts_property():
    """Test the `StepContext.inputs` property."""

    @pipeline
    def _pipeline():
        output = output_metadata_logging_step()
        step_context_metadata_reader_step(my_input=output)

    _pipeline()


@step
def step_context_metadata_and_tags_adder(
    name: Optional[str], metadata: Dict[str, Any], tags: List[str]
) -> Tuple[
    Annotated[
        str,
        ArtifactConfig(
            name="custom_name",
            run_metadata={"config_metadata": "bar"},
            tags=["config_tags"],
        ),
    ],
    str,
]:
    step_context = get_step_context()
    step_context.add_output_metadata(output_name=name, metadata=metadata)
    step_context.add_output_tags(output_name=name, tags=tags)
    return "bar", "foo"


@pytest.mark.parametrize(
    "inner_name,full_name,metadata,tags",
    [
        ["custom_name", "custom_name", {}, []],
        ["custom_name", "custom_name", {"some": "foo"}, []],
        ["custom_name", "custom_name", {}, ["foo"]],
        ["custom_name", "custom_name", {"some": "foo"}, ["foo"]],
        ["custom_name", "custom_name", {"some": "foo"}, ["foo", "foo"]],
        [
            "output_1",
            "_pipeline::step_context_metadata_and_tags_adder::output_1",
            {},
            [],
        ],
        [
            "output_1",
            "_pipeline::step_context_metadata_and_tags_adder::output_1",
            {"some": "foo"},
            [],
        ],
        [
            "output_1",
            "_pipeline::step_context_metadata_and_tags_adder::output_1",
            {},
            ["foo"],
        ],
        [
            "output_1",
            "_pipeline::step_context_metadata_and_tags_adder::output_1",
            {"some": "foo"},
            ["foo"],
        ],
        [
            "output_1",
            "_pipeline::step_context_metadata_and_tags_adder::output_1",
            {"some": "foo"},
            ["foo", "foo"],
        ],
    ],
    ids=[
        "Only custom name",
        "Custom name and metadata",
        "Custom name and tags",
        "Custom name, metadata and tags",
        "Custom name, metadata and duplicated tags",
        "Only standard name",
        "Standard name and metadata",
        "Standard name and tags",
        "Standard name, metadata and tags",
        "Standard name, metadata and duplicated tags",
    ],
)
def test_metadata_and_tags_set_from_context(
    clean_client: "Client",
    inner_name: str,
    full_name: str,
    metadata: Dict[str, Any],
    tags: List[str],
):
    @pipeline(enable_cache=False)
    def _pipeline():
        step_context_metadata_and_tags_adder(
            name=inner_name, metadata=metadata, tags=tags
        )

    _pipeline()

    av = clean_client.get_artifact_version(full_name)
    artifact = clean_client.get_artifact(full_name)
    for k, v in metadata.items():
        assert k in av.run_metadata
        assert av.run_metadata[k].value == v

    if full_name == "custom_name":
        assert av.run_metadata["config_metadata"].value == "bar"
        assert {t.name for t in av.tags} == set(tags).union({"config_tags"})
        assert {t.name for t in artifact.tags} == set(tags).union(
            {"config_tags"}
        )
    else:
        assert set(tags) == {t.name for t in av.tags}
        assert set(tags) == {t.name for t in artifact.tags}
