"""Verify qualification blocks GPU allocation and compile the actual artifact graph."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import native_training as workflow
import pytest
from pydantic import ValidationError

from zenml.models import ArtifactVersionResponse


def pilot_config() -> workflow.NativeTrainingConfig:
    """Load the documented bounded pilot configuration.

    Returns:
        Validated portable training configuration.
    """
    return workflow.NativeTrainingConfig.model_validate_json(
        (
            Path(__file__).parents[1] / "native-training.example.json"
        ).read_text()
    )


def test_native_graph_links_qualification_and_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compile real steps while replacing only the external artifact lookup.

    Args:
        monkeypatch: Scoped external lookup replacement.
    """
    identifier = UUID("11111111-1111-4111-8111-111111111111")
    artifact = ArtifactVersionResponse.model_construct(id=identifier)
    monkeypatch.setattr(
        workflow,
        "Client",
        lambda: SimpleNamespace(get_artifact_version=lambda _: artifact),
    )
    pipeline = workflow.endless_terminals_native_training.with_options()
    pipeline.prepare(bundle_artifact_id=identifier, config=pilot_config())
    invocations = pipeline.invocations
    assert set(invocations) == {
        "qualify_sandbox_initial",
        "reference_fixture",
        "noop_fixture",
        "report_sandbox_results",
        "train_native",
        "report_training",
    }
    assert (
        invocations["train_native"].external_artifacts["bundle"].id
        == identifier
    )
    dependencies = invocations["train_native"].input_artifacts
    assert set(dependencies) == {"initial", "reference", "noop"}
    initial_artifact = dependencies["initial"]
    assert not isinstance(initial_artifact, list)
    assert initial_artifact.output_name == "sandbox_initial_qualification"
    for name, output in {
        "before": "before_evaluation",
        "after_evaluation": "after_evaluation",
        "training": "training_evidence",
    }.items():
        input_artifact = invocations["report_training"].input_artifacts[name]
        assert not isinstance(input_artifact, list)
        assert input_artifact.output_name == output


@pytest.mark.parametrize(
    "failure", ["initial", "reference", "noop", "cleanup"]
)
def test_failed_qualification_never_constructs_gpu_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Reject each failed prerequisite before a GPU service can be created.

    Args:
        tmp_path: Stand-in bundle path.
        monkeypatch: Scoped task and allocation replacements.
        failure: Qualification boundary to fail.
    """
    task = {"task_id": workflow.PILOT_TASK, "dataset_revision": "a" * 40}
    initial: dict[str, Any] = {
        "task": task,
        "grading": {"audited_valid": True},
        "cleanup_complete": True,
    }
    reference: dict[str, Any] = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {"raw_reward": 1, "audited_valid": True},
    }
    noop: dict[str, Any] = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {
            "raw_reward": 0,
            "audited_valid": False,
            "test_counts": {"failure": 1},
        },
    }
    if failure == "initial":
        initial["grading"]["audited_valid"] = False
    elif failure == "cleanup":
        initial["cleanup_complete"] = False
    else:
        {"reference": reference, "noop": noop}[failure]["grading"][
            "infrastructure_error"
        ] = "failed"
    monkeypatch.setattr(workflow, "load_bundle_task", lambda *_: task)
    service = Mock()
    publish = Mock()
    monkeypatch.setattr(workflow, "NativeTrainingService", service)
    monkeypatch.setattr(workflow, "save_artifact", publish)
    with pytest.raises(RuntimeError, match="GPU service was not started"):
        workflow.train_native.entrypoint(
            tmp_path, initial, reference, noop, pilot_config()
        )
    service.assert_not_called()
    publish.assert_called_once()


def test_native_config_rejects_unqualified_task_selection() -> None:
    """Keep every task selection on the one verified canonical pilot."""
    config = pilot_config().model_dump(mode="json")
    config["training"]["training_task_ids"] = ["another-task"]
    with pytest.raises(ValidationError, match="canonical|native pilot"):
        workflow.NativeTrainingConfig.model_validate(config)


def test_successful_training_persists_initial_adapter_and_service_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain starting weights and GPU diagnostics before the controller disappears.

    Args:
        tmp_path: Temporary controller output directory.
        monkeypatch: Scoped replacements for external training and publishing.
    """
    task = {"task_id": workflow.PILOT_TASK, "dataset_revision": "a" * 40}
    initial: dict[str, Any] = {
        "task": task,
        "grading": {"audited_valid": True},
        "cleanup_complete": True,
    }
    reference: dict[str, Any] = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {"raw_reward": 1, "audited_valid": True},
    }
    noop: dict[str, Any] = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {
            "raw_reward": 0,
            "audited_valid": False,
            "test_counts": {"failure": 1},
        },
    }
    run_id = "native-test-run"
    directory = tmp_path / run_id
    diagnostics = directory / "service"
    monkeypatch.setattr(workflow, "load_bundle_task", lambda *_: task)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda **_: str(tmp_path))
    monkeypatch.setattr(
        workflow,
        "get_step_context",
        lambda: SimpleNamespace(pipeline_run=SimpleNamespace(id=run_id)),
    )
    monkeypatch.setattr(workflow, "NativeTrainingService", Mock())
    result: tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path] = (
        {"before": True},
        {"after": True},
        {},
        directory / "checkpoint",
    )

    def train(
        *args: object, **kwargs: object
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
        diagnostics.mkdir(parents=True)
        (diagnostics / "training-main.log").write_text("training completed")
        initial_adapter = directory / "initial_checkpoint"
        initial_adapter.mkdir()
        (initial_adapter / "adapter.safetensors").write_bytes(
            b"initial adapter"
        )
        return result

    def publish(path: Path, name: str) -> None:
        if name == "native_training_diagnostics":
            assert path == diagnostics
            assert (
                path / "training-main.log"
            ).read_text() == "training completed"
        else:
            assert name == "initial_adapter"
            assert path == directory / "initial_checkpoint"
            assert (
                path / "adapter.safetensors"
            ).read_bytes() == b"initial adapter"

    publish_mock = Mock(side_effect=publish)
    monkeypatch.setattr(workflow, "execute_training", train)
    monkeypatch.setattr(workflow, "save_artifact", publish_mock)
    assert (
        workflow.train_native.entrypoint(
            tmp_path, initial, reference, noop, pilot_config()
        )
        == result
    )
    assert {call.kwargs["name"] for call in publish_mock.call_args_list} == {
        "native_training_diagnostics",
        "initial_adapter",
    }
    assert publish_mock.call_count == 2


@pytest.mark.parametrize("field", ["modal_workspace", "modal_environment"])
def test_modal_service_and_task_identity_must_agree(field: str) -> None:
    """Reject mismatches before qualification or service allocation.

    Args:
        field: Sandbox identity field to mismatch.
    """
    import json

    values = json.loads(
        (Path(__file__).parents[1] / "modal-training.example.json").read_text()
    )
    values["service"].update(
        workspace="external-team", modal_environment="research"
    )
    values["sandbox"].update(
        modal_workspace="external-team", modal_environment="research"
    )
    config = workflow.NativeTrainingConfig.model_validate(values)
    assert config.sandbox.modal_workspace == "external-team"
    values["sandbox"][field] = "other"
    with pytest.raises(ValidationError, match="must match"):
        workflow.NativeTrainingConfig.model_validate(values)
