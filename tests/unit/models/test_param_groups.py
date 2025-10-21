from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.models import (
    ArtifactVersionIdentifier,
    ModelVersionIdentifier,
    PipelineRunIdentifier,
    StepRunIdentifier,
)


def test_versioned_identifier_validators():
    for cls in [ArtifactVersionIdentifier, ModelVersionIdentifier]:
        v_id = cls(id=uuid4())
        assert (
            v_id.id is not None and v_id.name is None and v_id.version is None
        )

        v_nv = cls(id=None, name="artifact", version="1.2.3")
        assert v_nv.name == "artifact" and v_nv.version == "1.2.3"

        with pytest.raises(ValidationError):
            cls(id=uuid4(), name="artifact", version="1.0")

        with pytest.raises(ValidationError):
            cls(id=None, name=None, version=None)

        with pytest.raises(ValidationError):
            cls(name="artifact")

        with pytest.raises(ValidationError):
            cls(version="1.0.0")


def test_pipeline_run_identifier_validators():
    pid = uuid4()
    p_id_only = PipelineRunIdentifier(id=pid)
    assert p_id_only.value == pid  # value prioritizes id

    p_name_only = PipelineRunIdentifier(name="nightly")
    assert p_name_only.value == "nightly"

    p_prefix_only = PipelineRunIdentifier(
        id=None, name=None, prefix="nightly-2025-10"
    )
    assert p_prefix_only.value == "nightly-2025-10"

    p_all_order = PipelineRunIdentifier(id=pid, name=None, prefix=None)
    assert p_all_order.value == pid

    with pytest.raises(ValidationError):
        PipelineRunIdentifier(id=uuid4(), name="n", prefix=None)

    with pytest.raises(ValidationError):
        PipelineRunIdentifier(id=None, name="n", prefix="p")

    with pytest.raises(ValidationError):
        PipelineRunIdentifier(id=uuid4(), name=None, prefix="p")

    with pytest.raises(ValidationError):
        PipelineRunIdentifier(id=uuid4(), name="n", prefix="p")

    with pytest.raises(ValidationError):
        PipelineRunIdentifier(id=None, name=None, prefix=None)


def test_step_run_identifier_validators():
    id_ = uuid4()

    s_id_only = StepRunIdentifier(id=id_)

    assert s_id_only.id == id_

    run_ident = PipelineRunIdentifier(id=None, name="nightly", prefix=None)

    s_name_with_pipeline = StepRunIdentifier(
        id=None, name="load_data", run=run_ident
    )
    assert s_name_with_pipeline.id is None
    assert s_name_with_pipeline.name == "load_data"
    assert isinstance(s_name_with_pipeline.run, PipelineRunIdentifier)

    with pytest.raises(ValidationError):
        StepRunIdentifier(id=uuid4(), name="transform", run=run_ident)

    with pytest.raises(ValidationError):
        StepRunIdentifier(id=None, name="")

    with pytest.raises(ValidationError):
        StepRunIdentifier(id=None, name="train_model")

    with pytest.raises(ValidationError):
        StepRunIdentifier(id=None, run=run_ident)
