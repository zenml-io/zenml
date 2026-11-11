"""Check unsafe and ambiguous managed model requests at the API boundary."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.models.managed_model import (
    ManagedModelMutation,
    ManagedModelServiceRequest,
    ModelArtifactReference,
)


def test_artifact_reference_rejects_escape_paths():
    """An artifact ID must not authorize neighboring files or URLs."""
    for path in (
        "../secret",
        "/bucket",
        "s3://bucket",
        "a//b",
        "a/../b",
        "%2e%2e/a",
    ):
        with pytest.raises(ValidationError):
            ModelArtifactReference(artifact_version_id=uuid4(), path=path)


def test_adapter_requires_pinned_base_and_explicit_tokenizer():
    """An adapter alone is not a reproducible model package."""
    request = dict(
        project_id=uuid4(),
        model_deployer_id=uuid4(),
        name="test",
        serving_profile="chat-v1",
        package={
            "kind": "peft_lora",
            "model": {"artifact_version_id": uuid4()},
        },
    )
    with pytest.raises(ValidationError):
        ManagedModelServiceRequest(**request)
    request["package"].update(
        base_model={"repository": "org/model", "revision": "main"},
        tokenizer={"artifact_version_id": uuid4()},
    )
    with pytest.raises(ValidationError):
        ManagedModelServiceRequest(**request)
    request["package"]["base_model"]["revision"] = "a" * 40
    model = ManagedModelServiceRequest(**request)
    assert (
        ManagedModelServiceRequest.model_validate_json(model.model_dump_json())
        == model
    )


def test_package_does_not_accept_credentials_or_provider_commands():
    """Provider configuration cannot be smuggled through the package DTO."""
    artifact = {"artifact_version_id": uuid4()}
    with pytest.raises(ValidationError):
        ManagedModelServiceRequest(
            project_id=uuid4(),
            model_deployer_id=uuid4(),
            name="test",
            serving_profile="chat-v1",
            package={
                "kind": "transformers",
                "model": artifact,
                "tokenizer": artifact,
                "aws_secret_access_key": "synthetic",
            },
        )


def test_mutations_reject_ambiguous_revision_selection():
    """Pause and rollback must not silently accept update payloads."""
    with pytest.raises(ValidationError):
        ManagedModelMutation(action="rollback", expected_generation=1)
    with pytest.raises(ValidationError):
        ManagedModelMutation(
            action="pause", expected_generation=1, revision_id=uuid4()
        )
    with pytest.raises(ValidationError):
        ManagedModelMutation(action="update", expected_generation=1)
