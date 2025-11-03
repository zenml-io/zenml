from uuid import uuid4

from zenml.enums import MetadataResourceTypes
from zenml.models import RunMetadataResource


def test_run_metadata_resource_equality_and_hash():
    """Test equality and hash behavior of RunMetadataResource."""

    # --- Setup ---
    id1 = uuid4()
    id2 = uuid4()

    r1 = RunMetadataResource(id=id1, type=MetadataResourceTypes.STEP_RUN)
    r2 = RunMetadataResource(id=id1, type=MetadataResourceTypes.STEP_RUN)
    r3 = RunMetadataResource(id=id2, type=MetadataResourceTypes.STEP_RUN)
    r4 = RunMetadataResource(
        id=id1, type=MetadataResourceTypes.ARTIFACT_VERSION
    )

    assert r1 == r2, "Objects with same id and type should be equal"
    assert hash(r1) == hash(r2), "Hashes should be equal for identical objects"

    assert r1 != r3, "Objects with different ids should not be equal"
    assert hash(r1) != hash(r3), "Hashes should differ for different ids"

    assert r1 != r4, (
        "Objects with same id but different type should not be equal"
    )
    assert hash(r1) != hash(r4), "Hashes should differ for different types"

    assert r1 != 1

    s = {r1, r2, r3}
    assert len(s) == 2, "Set should treat r1 and r2 as the same object"

    d = {r1: "A", r3: "B"}
    assert d[r2] == "A", "Dict should retrieve same value for equal objects"
