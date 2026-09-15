"""Compile the real pipeline boundary without uploading or querying artifacts."""

from types import SimpleNamespace
from uuid import UUID

import pytest
import sandbox_pipeline as workflow
from pydantic import ValidationError

from zenml.models import ArtifactVersionResponse


def test_prepare_accepts_bundle_artifact_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compile real steps with a stored artifact response and JSON-safe inputs.

    Args:
        monkeypatch: Replace only the external artifact lookup.
    """
    identifier = UUID("11111111-1111-4111-8111-111111111111")
    artifact = ArtifactVersionResponse.model_construct(id=identifier)
    requested = []

    def lookup(value: UUID) -> ArtifactVersionResponse:
        """Return the test artifact response.

        Args:
            value: Requested artifact version ID.

        Returns:
            Existing artifact response fixture.
        """
        requested.append(value)
        return artifact

    monkeypatch.setattr(
        workflow,
        "Client",
        lambda: SimpleNamespace(get_artifact_version=lookup),
    )
    pipeline = workflow.endless_terminals_sandbox.with_options()
    pipeline.prepare(
        bundle_artifact_id=identifier,
        config=workflow.SandboxPipelineConfig(
            helper_image="registry/helper@sha256:" + "a" * 64
        ),
    )
    assert requested == [identifier]
    invocations = pipeline.invocations
    assert set(invocations) == {
        "qualify_sandbox_initial",
        "reference_fixture",
        "noop_fixture",
        "report_sandbox_results",
    }
    for name in (
        "qualify_sandbox_initial",
        "reference_fixture",
        "noop_fixture",
    ):
        assert invocations[name].external_artifacts["bundle"].id == identifier
    assert set(invocations["report_sandbox_results"].input_artifacts) == {
        "initial",
        "reference",
        "noop",
    }


def test_config_rejects_mutable_image_and_multiple_tasks() -> None:
    """Reject an unpinned helper and accidental expansion beyond one task."""
    with pytest.raises(ValidationError):
        workflow.SandboxPipelineConfig(helper_image="registry/helper:latest")
    with pytest.raises(ValidationError):
        workflow.SandboxPipelineConfig(
            helper_image="registry/helper@sha256:" + "a" * 64,
            task_ids=["task-one", "task-two"],
        )


def test_environment_receives_modal_agent_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The serialized pipeline option reaches the runtime without allocation.

    Args:
        monkeypatch: Replace the allocating runtime boundary.
    """
    from unittest.mock import Mock

    from runtime import sandbox_env

    factory = Mock()
    monkeypatch.setattr(sandbox_env, "SandboxEnvironment", factory)
    image = "registry/agent@sha256:" + "b" * 64
    workflow.create_environment(
        {"image_ref": "registry/task@sha256:" + "c" * 64},
        workflow.SandboxPipelineConfig(
            helper_image="registry/helper@sha256:" + "a" * 64,
            modal_agent_image=image,
            modal_workspace="external-team",
            modal_environment="research",
        ),
    )
    assert factory.call_args.kwargs["config"].modal_agent_image == image
    assert (
        factory.call_args.kwargs["config"].modal_workspace == "external-team"
    )
    assert factory.call_args.kwargs["config"].modal_environment == "research"
    with pytest.raises(ValidationError):
        workflow.SandboxPipelineConfig(
            helper_image="registry/helper@sha256:" + "a" * 64,
            modal_agent_image="registry/agent:latest",
        )
