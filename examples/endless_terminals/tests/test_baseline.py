"""Check immutable sampling, budget coverage, qualification, and cleanup."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import baseline as workflow
import pytest
from pydantic import ValidationError

from zenml.models import ArtifactVersionResponse


def baseline_config() -> workflow.BaselineConfig:
    """Return a small representative fixed-protocol configuration.

    Returns:
        Two-task baseline settings without external resources.
    """
    image = "registry/image@sha256:" + "a" * 64
    return workflow.BaselineConfig(
        controller_image=image,
        task_ids=["one", "two"],
        sandbox={"helper_image": image},
        service={"training_image": image},
        modal_agent_images={
            "one": image,
            "two": "registry/two@sha256:" + "b" * 64,
        },
    )


def install_runtime(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace external services while preserving executor control flow.

    Args:
        monkeypatch: Scoped replacements.

    Returns:
        Inspectable runtime doubles and qualified task evidence.
    """
    tasks: list[dict[str, Any]] = [
        {
            "task_id": name,
            "dataset_revision": "c" * 40,
            "task_file_sha256": {},
            "image_ref": "registry/" + name + "@sha256:" + "a" * 64,
        }
        for name in ("one", "two")
    ]

    def initial(task: dict[str, Any]) -> dict[str, Any]:
        """Return clean initial-state qualification evidence.

        Args:
            task: Immutable task identity.

        Returns:
            Passing initial-state result.
        """
        return {
            "task": task,
            "cleanup_complete": True,
            "grading": {"audited_valid": True},
        }

    reference = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {"raw_reward": 1, "audited_valid": True},
    }
    noop = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {
            "raw_reward": 0,
            "audited_valid": False,
            "test_counts": {"failure": 1},
        },
    }
    qualification = {
        "qualified": ["one", "two"],
        "rejected": [],
        "tasks": [
            {
                "task": task,
                "qualified": True,
                "initial": initial(task),
                "reference": reference,
                "noop": noop,
            }
            for task in tasks
        ],
    }
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    session.serving_seconds_remaining = 5000
    session.base_url = "https://service.example"
    session.api_key = "private"
    session.service_host = "service.example"
    session.identity = {"backend": "test"}
    session.cleanup_report = {"complete": True}
    constructor = Mock(return_value=session)
    policy = Mock(optimizer_steps=0)
    snapshot = {
        "identity": {"optimizer_steps": 0, "path": "unchanged"},
        "client": object(),
    }
    policy.snapshot.return_value = snapshot
    calls: list[tuple[str, Path]] = []

    def episode(
        task: dict[str, Any],
        directory: Path,
        model: Any,
        output: Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        calls.append((task["task_id"], output))
        return {
            "task_id": task["task_id"],
            "cleanup_complete": True,
            "grading": {
                "audited_valid": task["task_id"] == "one",
                "raw_reward": int(task["task_id"] == "one"),
            },
            "turns": [],
            "exit_reason": "done",
        }

    monkeypatch.setattr(workflow, "ModalTrainingService", constructor)
    monkeypatch.setattr(workflow, "TinkerPolicy", Mock(return_value=policy))
    monkeypatch.setattr(
        workflow,
        "load_bundle_task",
        lambda bundle, settings: next(
            task for task in tasks if task["task_id"] == settings.task_ids[0]
        ),
    )
    monkeypatch.setattr(workflow, "run_episode", episode)
    monkeypatch.setattr(workflow, "save_artifact", Mock())
    return SimpleNamespace(
        session=session,
        constructor=constructor,
        policy=policy,
        qualification=qualification,
        calls=calls,
    )


def test_round_robin_never_updates_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every task receives three independent attempts from one unchanged sampler.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    result = workflow.execute_baseline(
        tmp_path,
        runtime.qualification,
        baseline_config(),
        "run",
        tmp_path / "output",
    )
    assert [task for task, _ in runtime.calls] == ["one", "two"] * 3
    assert len({path for _, path in runtime.calls}) == 6
    assert result["status"] == "completed"
    assert result["summary"]["tasks"]["one"]["passes"] == 3
    assert result["summary"]["tasks"]["two"]["failures"] == 3
    runtime.policy.snapshot.assert_called_once()
    runtime.policy.update.assert_not_called()
    runtime.policy.download_checkpoint.assert_not_called()
    assert (
        len(
            {
                id(call.args[0])
                for call in runtime.policy.episode_model.call_args_list
            }
        )
        == 1
    )


def test_deadline_retains_unattempted_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exhausted service budget returns explicit partial evidence.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    runtime.session.serving_seconds_remaining = 389
    result = workflow.execute_baseline(
        tmp_path,
        runtime.qualification,
        baseline_config(),
        "run",
        tmp_path / "output",
    )
    assert result["status"] == "bounded_partial"
    assert len(result["unattempted"]) == 6
    assert not runtime.calls
    assert result["cleanup"]["complete"] is True
    assert (
        json.loads((tmp_path / "output/evaluation.json").read_text())["status"]
        == "bounded_partial"
    )


@pytest.mark.parametrize("failure", ["qualification", "identity"])
def test_qualification_failure_prevents_gpu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Rejected or altered tasks cannot allocate a GPU service.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
        failure: Failure case under test.
    """
    runtime = install_runtime(monkeypatch)
    if failure == "qualification":
        runtime.qualification["tasks"][0]["initial"]["cleanup_complete"] = (
            False
        )
    else:
        runtime.qualification["tasks"][0]["task"] = {
            **runtime.qualification["tasks"][0]["task"],
            "image_ref": "changed",
        }
    with pytest.raises(RuntimeError, match="GPU service was not started"):
        workflow.execute_baseline(
            tmp_path,
            runtime.qualification,
            baseline_config(),
            "run",
            tmp_path / "output",
        )
    runtime.constructor.assert_not_called()


def test_cleanup_failure_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incomplete GPU cleanup fails after durable evidence is written.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    runtime.session.cleanup_report = {"complete": False}
    with pytest.raises(RuntimeError, match="cleanup incomplete"):
        workflow.execute_baseline(
            tmp_path,
            runtime.qualification,
            baseline_config(),
            "run",
            tmp_path / "output",
        )
    evidence = json.loads((tmp_path / "output/evaluation.json").read_text())
    assert evidence["status"] == "failed"
    assert len(evidence["episodes"]) == 6


def test_provider_exception_retains_partial_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected provider failure preserves coverage and closes the service.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    monkeypatch.setattr(
        workflow,
        "run_episode",
        Mock(side_effect=RuntimeError("provider unavailable")),
    )
    with pytest.raises(RuntimeError, match="provider unavailable"):
        workflow.execute_baseline(
            tmp_path,
            runtime.qualification,
            baseline_config(),
            "run",
            tmp_path / "output",
        )
    runtime.session.__exit__.assert_called_once()
    evidence = json.loads((tmp_path / "output/evaluation.json").read_text())
    assert evidence["status"] == "failed"
    assert len(evidence["unattempted"]) == 6
    assert evidence["cleanup"]["complete"] is False
    assert evidence["cleanup"]["interrupted_attempt"] == {
        "task_id": "one",
        "attempt_index": 1,
    }


def test_task_images_and_protocol_are_validated() -> None:
    """Task overrides remain distinct and immutable sampling limits are enforced."""
    config = baseline_config()
    assert (
        config.task_config("one").modal_agent_image
        == "registry/image@sha256:" + "a" * 64
    )
    assert (
        config.task_config("two").modal_agent_image
        == "registry/two@sha256:" + "b" * 64
    )
    with pytest.raises(ValidationError):
        workflow.BaselineConfig.model_validate(
            {**config.model_dump(), "temperature": 1.0}
        )
    with pytest.raises(ValidationError):
        workflow.BaselineConfig.model_validate(
            {
                **config.model_dump(),
                "modal_agent_images": {"one": "mutable:latest"},
            }
        )


def test_graph_requires_qualification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compile the real artifact dependency that gates GPU allocation.

    Args:
        monkeypatch: Scoped runtime replacements.
    """
    identifier = UUID("11111111-1111-4111-8111-111111111111")
    artifact = ArtifactVersionResponse.model_construct(id=identifier)
    monkeypatch.setattr(
        workflow,
        "Client",
        lambda: SimpleNamespace(get_artifact_version=lambda _: artifact),
    )
    pipeline = workflow.endless_terminals_modal_baseline.with_options()
    pipeline.prepare(bundle_artifact_id=identifier, config=baseline_config())
    assert set(pipeline.invocations) == {
        "qualify_baseline_tasks",
        "evaluate_baseline",
    }
    assert (
        "qualification"
        in pipeline.invocations["evaluate_baseline"].input_artifacts
    )


def test_rejected_task_is_excluded_after_clean_qualification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad reference excludes that task while clean tasks remain eligible.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    runtime.qualification["tasks"][0]["reference"] = {
        "exit_reason": "done",
        "cleanup_complete": True,
        "grading": {"raw_reward": 0, "audited_valid": False},
    }
    result = workflow.execute_baseline(
        tmp_path,
        runtime.qualification,
        baseline_config(),
        "run",
        tmp_path / "output",
    )
    assert result["selected_task_ids"] == ["two"]
    assert [task for task, _ in runtime.calls] == ["two"] * 3


def test_infrastructure_episode_is_separate_from_task_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid grading cannot become a task failure or pass.

    Args:
        tmp_path: Isolated evidence directory.
        monkeypatch: Scoped runtime replacements.
    """
    runtime = install_runtime(monkeypatch)
    monkeypatch.setattr(
        workflow,
        "run_episode",
        lambda task, *args, **kwargs: {
            "task_id": task["task_id"],
            "cleanup_complete": True,
            "exit_reason": "provider_error",
            "infrastructure_error": "provider unavailable",
        },
    )
    result = workflow.execute_baseline(
        tmp_path,
        runtime.qualification,
        baseline_config(),
        "run",
        tmp_path / "output",
    )
    assert result["summary"]["infrastructure_errors"] == 6
    assert result["summary"]["failures"] == 0
    assert result["summary"]["passes"] == 0
    report = (tmp_path / "output/report.html").read_text()
    assert "one / attempt 1" in report
    assert "Unattempted" in report


@pytest.mark.parametrize("field", ["modal_workspace", "modal_environment"])
def test_modal_baseline_identity_must_agree(field: str) -> None:
    """Require one workspace and environment throughout baseline execution.

    Args:
        field: Sandbox identity field to mismatch.
    """
    values = baseline_config().model_dump()
    values["service"].update(
        workspace="external-team", modal_environment="research"
    )
    values["sandbox"].update(
        modal_workspace="external-team", modal_environment="research"
    )
    config = workflow.BaselineConfig.model_validate(values)
    assert config.task_config("one").modal_workspace == "external-team"
    assert config.task_config("one").modal_environment == "research"
    values["sandbox"][field] = "other"
    with pytest.raises(ValidationError, match="must match"):
        workflow.BaselineConfig.model_validate(values)
