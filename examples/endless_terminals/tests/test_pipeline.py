"""Verify lifecycle failures remain failed runs with inspectable evidence."""

import json
from pathlib import Path
from unittest.mock import Mock

import pipeline as workflow
import pytest
from config import EvaluationConfig


def test_fixture_failure_persists_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incorrect reference solution must not produce a green smoke run.

    Args:
        tmp_path: Test directory.
        monkeypatch: Scoped patches.
    """
    directory = tmp_path / "task" / "solution"
    directory.mkdir(parents=True)
    (directory / "solve.sh").write_text("false")
    monkeypatch.setattr(
        workflow,
        "run_episode",
        lambda *args, **kwargs: {
            "task_id": "task",
            "grading": {"raw_reward": 0, "audited_valid": False},
            "cleanup_complete": True,
            "exit_reason": "done",
            "turns": [],
        },
    )
    upload = Mock()
    monkeypatch.setattr(workflow, "save_artifact", upload)
    prepared = {
        "dataset_revision": "pinned",
        "tasks": [
            {
                "task_id": "task",
                "task_file_sha256": {},
                "local_image_id": "sha256:1",
            }
        ],
    }
    config = EvaluationConfig(
        data_directory=str(tmp_path), output_directory=str(tmp_path / "runs")
    )
    with pytest.raises(RuntimeError, match="Reference fixture failed"):
        workflow.execute_evaluation(prepared, config, "run")
    result = json.loads((tmp_path / "runs/run/evaluation.json").read_text())
    assert result["status"] == "failed"
    assert len(result["episodes"]) == 1
    assert upload.call_count == 2


def test_cloud_startup_failure_retains_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain cleanup evidence when the inference context fails to enter.

    Args:
        tmp_path: Test directory.
        monkeypatch: Scoped patches.
    """
    cloud_file = tmp_path / "cloud.json"
    cloud_file.write_text(json.dumps({"vllm_image": "pinned"}))
    session = Mock()
    session.cleanup_report = {"complete": True, "job_deleted": True}
    session.__enter__ = Mock(side_effect=RuntimeError("startup failed"))
    session.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(
        workflow, "KubernetesInference", Mock(return_value=session)
    )
    monkeypatch.setattr(workflow, "save_artifact", Mock())
    episode = Mock()
    monkeypatch.setattr(workflow, "run_episode", episode)
    config = EvaluationConfig(
        mode="kubernetes",
        cloud_config_path=str(cloud_file),
        output_directory=str(tmp_path / "runs"),
    )
    with pytest.raises(RuntimeError, match="startup failed"):
        workflow.execute_evaluation(
            {"dataset_revision": "pinned", "tasks": []}, config, "run"
        )
    result = json.loads((tmp_path / "runs/run/evaluation.json").read_text())
    assert result["cleanup"]["complete"] is True
    assert result["status"] == "failed"
    episode.assert_not_called()


def test_custom_model_requires_revision() -> None:
    """Do not attach the default Qwen revision to a different model."""
    with pytest.raises(ValueError, match="explicit model_revision"):
        EvaluationConfig(model_name="another/model")
