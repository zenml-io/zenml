"""Exercise paired training lifecycle without model or cloud requests."""

import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import Mock

import pytest
import training
from config import TrainingConfig
from reporting import render_evaluation_report
from runtime.contract import SYSTEM_MESSAGE


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Prepare fake policy and cloud boundaries around the real training loop.

    Args:
        tmp_path: Temporary artifact directory.
        monkeypatch: Scoped patch helper.

    Returns:
        Configuration, prepared tasks, and mocked external dependencies.
    """
    cloud = tmp_path / "cloud.json"
    cloud.write_text(json.dumps({"training_image": "image@sha256:abc"}))
    config = TrainingConfig(
        cloud_config_path=str(cloud),
        data_directory=str(tmp_path / "data"),
        output_directory=str(tmp_path / "runs"),
        training_task_ids=["task-a"],
        groups=3,
        group_size=2,
        zero_signal_patience=2,
    )
    prepared = {
        "dataset_revision": "dataset-1",
        "tasks": [
            {
                "task_id": "task-a",
                "task_file_sha256": {"instruction.md": "hash"},
                "local_image_id": "image-id",
            }
        ],
    }
    session = Mock()
    session.serving_seconds_remaining = 100000
    session.base_url = "http://localhost:1234"
    session.identity = {"job_name": "owned-test-job"}
    session.cleanup_report = {"complete": False}
    session.__enter__ = Mock(return_value=session)

    def cleanup(*args: Any) -> None:
        session.cleanup_report = {"complete": True}

    session.__exit__ = Mock(side_effect=cleanup)
    service_constructor = Mock(return_value=session)
    monkeypatch.setattr(training, "KubernetesInference", service_constructor)
    policy = Mock()
    policy.optimizer_steps = 0
    policy.snapshot.side_effect = lambda name, **kwargs: {
        "identity": {"path": name},
        "client": "fake-client",
    }
    policy.episode_model.side_effect = lambda snapshot: SimpleNamespace(
        samples=[
            {
                "checkpoint": snapshot["identity"]["path"],
                "prompt_ids": [1],
                "completion_ids": [2],
                "logprobs": [-0.5],
            }
        ]
    )

    def update(samples: list[Any], rewards: list[float]) -> dict[str, Any]:
        changed = len(set(rewards)) > 1
        policy.optimizer_steps += int(changed)
        return {"updated": changed, "optimizer_steps": policy.optimizer_steps}

    policy.update.side_effect = update

    def download(name: str, directory: Path) -> Path:
        directory.mkdir(parents=True)
        manifest = directory / "manifest.json"
        manifest.write_text(
            json.dumps(
                {"kind": "sampler_adapter_not_resume_checkpoint", "name": name}
            )
        )
        (directory / "adapter.safetensors").write_bytes(name.encode())
        return manifest

    policy.download_checkpoint.side_effect = download
    policy_constructor = Mock(return_value=policy)
    artifact_publisher = Mock()
    monkeypatch.setattr(training, "TinkerPolicy", policy_constructor)
    monkeypatch.setattr(training, "save_artifact", artifact_publisher)
    rewards = [0, 0, 0, 0, 0, 0]

    def episode(
        task: dict[str, Any],
        directory: Path,
        model: Any,
        output: Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        reward = rewards.pop(0) if "training" in output.parts else 0
        return {
            "task_id": task["task_id"],
            "grading": {"raw_reward": reward, "audited_valid": bool(reward)},
            "cleanup_complete": True,
            "turns": [],
            "elapsed_seconds": 1,
            "exit_reason": "done",
        }

    episode_runner = Mock(side_effect=episode)
    monkeypatch.setattr(training, "run_episode", episode_runner)
    return SimpleNamespace(
        service_constructor=service_constructor,
        policy_constructor=policy_constructor,
        artifact_publisher=artifact_publisher,
        episode_runner=episode_runner,
        config=config,
        prepared=prepared,
        session=session,
        policy=policy,
        rewards=rewards,
        root=tmp_path,
    )


def test_zero_signal_stops_without_optimizer_updates(
    setup: SimpleNamespace,
) -> None:
    """Repeated equal rewards stop at patience while retaining paired evaluations.

    Args:
        setup: Isolated training fixture.
    """
    before, after, evidence, _ = training.execute_training(
        setup.prepared, setup.config, "zero"
    )
    assert evidence["optimizer_steps"] == 0
    setup.policy.snapshot.assert_called_once_with("before", timeout=600)
    assert evidence["stop_reason"] == "no_reward_variation"
    assert len(evidence["groups"]) == 2
    assert before["protocol"] == after["protocol"]
    assert before["task_hashes"] == after["task_hashes"]
    assert before["cleanup"]["complete"] is True
    setup.session.__exit__.assert_called_once()
    assert (
        json.loads((setup.root / "runs/zero/training.json").read_text())[
            "status"
        ]
        == "completed"
    )


def test_updates_use_new_snapshot(setup: SimpleNamespace) -> None:
    """Later groups and the final evaluation use the updated sampling checkpoint.

    Args:
        setup: Isolated training fixture.
    """
    setup.rewards[:] = [0, 1, 0, 1, 0, 1]
    before, after, evidence, _ = training.execute_training(
        setup.prepared, setup.config, "updated"
    )
    assert evidence["optimizer_steps"] == 3
    assert evidence["groups"][0]["samples"][0][0]["logprobs"] == [-0.5]
    assert [group["checkpoint"]["path"] for group in evidence["groups"]] == [
        "before",
        "update-01",
        "update-02",
    ]
    assert before["model"]["checkpoint"]["path"] == "before"
    assert after["model"]["checkpoint"]["path"] == "update-03"
    assert [call.args[0] for call in setup.policy.snapshot.call_args_list] == [
        "before",
        "update-01",
        "update-02",
        "update-03",
    ]


def test_update_failure_cleans_up_and_retains_partial_evidence(
    setup: SimpleNamespace,
) -> None:
    """A failed optimizer operation does not bypass owned service cleanup.

    Args:
        setup: Isolated training fixture.
    """
    setup.rewards[:] = [0, 1]
    setup.policy.update.side_effect = TimeoutError("uncertain update")
    with pytest.raises(TimeoutError, match="uncertain"):
        training.execute_training(setup.prepared, setup.config, "failed")
    evidence = json.loads(
        (setup.root / "runs/failed/training.json").read_text()
    )
    assert evidence["status"] == "failed"
    assert evidence["error"] == {
        "type": "TimeoutError",
        "message": "uncertain update",
    }
    assert evidence["cleanup"]["complete"] is True
    assert len(evidence["groups"][0]["episodes"]) == 2
    setup.policy.update.assert_called_once()
    setup.policy.download_checkpoint.assert_called_once_with(
        "initial", setup.root / "runs/failed/initial_checkpoint"
    )
    assert evidence["initial_checkpoint"]["name"] == "initial"
    setup.session.__exit__.assert_called_once()


def test_service_budget_stops_before_new_training_group(
    setup: SimpleNamespace,
) -> None:
    """Reserve the service lifetime before adding more training episodes.

    Args:
        setup: Isolated training fixture.
    """
    setup.session.serving_seconds_remaining = (
        setup.config.episode_timeout + 310
    )
    _, _, evidence, _ = training.execute_training(
        setup.prepared, setup.config, "budget"
    )
    assert evidence["stop_reason"] == "service_budget"
    assert evidence["groups"] == []
    setup.policy.update.assert_not_called()


def test_native_pipeline_builds_separate_artifact_dependencies(
    setup: SimpleNamespace,
) -> None:
    """Build the actual ZenML graph without allocating any cloud service.

    Args:
        setup: Mocked task and service boundaries.
    """
    workflow = training.endless_terminals_training
    workflow.prepare(setup.config)
    assert set(workflow.invocations) == {
        "prepare_evaluation",
        "train_and_evaluate",
        "report_training",
    }
    assert set(training.train_and_evaluate.entrypoint_definition.outputs) == {
        "before_evaluation",
        "after_evaluation",
        "training_evidence",
        "trained_adapter",
    }
    inputs = workflow.invocations["report_training"].input_artifacts
    for name, expected in {
        "before": "before_evaluation",
        "after_evaluation": "after_evaluation",
        "training": "training_evidence",
    }.items():
        artifact = inputs[name]
        assert not isinstance(artifact, list)
        assert artifact.output_name == expected
    setup.session.__enter__.assert_not_called()


def test_injected_environment_used_for_before_groups_and_after(
    setup: SimpleNamespace,
) -> None:
    """Use portable bundle paths and the sandbox factory for every model episode.

    Args:
        setup: Isolated training fixture.
    """
    setup.session.identity["training_image"] = (
        "registry/training@sha256:" + "a" * 64
    )
    setup.prepared["tasks"][0]["image_ref"] = (
        "registry/task@sha256:" + "b" * 64
    )
    bundle = setup.root / "materialized-bundle"
    factory = Mock()
    before, after, evidence, checkpoint = training.execute_training(
        setup.prepared,
        setup.config,
        "injected",
        session=setup.session,
        environment_factory=factory,
        data_directory=bundle,
        output_directory=setup.root / "native-output",
        client_api_key="run-secret",
        trusted_service_host="service.namespace.svc",
    )
    setup.service_constructor.assert_not_called()
    calls = setup.episode_runner.call_args_list
    assert len(calls) == 6
    assert all(call.args[1] == bundle / "task-a" for call in calls)
    assert all(call.kwargs["environment_factory"] is factory for call in calls)
    assert calls[0].args[3].name == "task-a"
    assert calls[-1].args[3].parent.name == "after"
    assert before["task_hashes"] == after["task_hashes"]
    assert (
        before["task_hashes"]["task-a"]["image"]
        == setup.prepared["tasks"][0]["image_ref"]
    )
    assert evidence["optimizer_steps"] == 0
    assert checkpoint.is_dir()
    assert setup.policy_constructor.call_args.kwargs["api_key"] == "run-secret"
    assert (
        setup.policy_constructor.call_args.kwargs["trusted_service_host"]
        == "service.namespace.svc"
    )


def test_injected_update_failure_publishes_diagnostics_after_cleanup(
    setup: SimpleNamespace,
) -> None:
    """Preserve remote-step failure evidence after releasing the injected service.

    Args:
        setup: Isolated training fixture.
    """
    setup.session.identity["training_image"] = (
        "registry/training@sha256:" + "a" * 64
    )
    setup.rewards[:] = [0, 1]
    setup.policy.update.side_effect = TimeoutError("uncertain native update")
    output = setup.root / "native-failure"
    with pytest.raises(TimeoutError, match="uncertain native update"):
        training.execute_training(
            setup.prepared,
            setup.config,
            "failed-native",
            session=setup.session,
            output_directory=output,
            data_directory=setup.root / "bundle",
            environment_factory=Mock(),
        )
    setup.session.__exit__.assert_called_once()
    evidence = json.loads((output / "training.json").read_text())
    assert evidence["cleanup"]["complete"] is True
    assert evidence["optimizer_steps"] == 0
    assert [
        call.kwargs["name"] for call in setup.artifact_publisher.call_args_list
    ] == ["failed_training_evidence", "failed_training_diagnostics"]
    assert setup.artifact_publisher.call_args.args[0] == output
    assert evidence["initial_checkpoint"]["name"] == "initial"
    assert (
        output / "initial_checkpoint/adapter.safetensors"
    ).read_bytes() == b"initial"
    setup.policy.download_checkpoint.assert_called_once_with(
        "initial", output / "initial_checkpoint"
    )


@pytest.mark.parametrize("variant", ["upstream", "concise_xml_v1"])
def test_prompt_variant_reaches_every_episode(
    setup: SimpleNamespace, variant: str
) -> None:
    """Use one explicit prompt across the before, training, and after episodes.

    Args:
        setup: Isolated training fixture.
        variant: Selected training prompt.
    """
    config = TrainingConfig.model_validate(
        {**setup.config.model_dump(), "prompt_variant": variant}
    )
    before, after, evidence, _ = training.execute_training(
        setup.prepared, config, "prompt"
    )
    calls = setup.episode_runner.call_args_list
    assert len(calls) == 6
    messages = [call.kwargs["system_message"] for call in calls]
    assert len(set(messages)) == 1
    if variant == "upstream":
        assert messages[0] == SYSTEM_MESSAGE
    else:
        from runtime.contract import CONCISE_XML_V1_SYSTEM_MESSAGE

        assert messages[0] == CONCISE_XML_V1_SYSTEM_MESSAGE
    digest = hashlib.sha256(messages[0].encode()).hexdigest()
    for protocol in (
        before["protocol"],
        after["protocol"],
        evidence["protocol"],
    ):
        assert protocol["prompt_variant"] == variant
        assert protocol["system_prompt_sha256"] == digest
    for key in ("prompt_variant", "system_prompt_sha256"):
        mismatched = {
            **after,
            "protocol": {**after["protocol"], key: "different"},
        }
        with pytest.raises(ValueError, match="protocol"):
            render_evaluation_report(mismatched, before)


def test_prompt_variant_default_and_validation(setup: SimpleNamespace) -> None:
    """Reject an unknown prompt variant before any training allocation.

    Args:
        setup: Isolated training fixture.
    """
    assert setup.config.prompt_variant == "upstream"
    with pytest.raises(ValueError, match="prompt_variant"):
        TrainingConfig.model_validate(
            {**setup.config.model_dump(), "prompt_variant": "unknown"}
        )
    setup.service_constructor.assert_not_called()


def test_initial_adapter_is_retained_before_any_training_episode(
    setup: SimpleNamespace,
) -> None:
    """Export and persist the starting weights between before evaluation and updates.

    Args:
        setup: Isolated training fixture.
    """
    output = setup.root / "runs/initial-retention"
    original_download: Callable[[str, Path], Path] = (
        setup.policy.download_checkpoint.side_effect
    )
    original_episode: Callable[..., dict[str, Any]] = (
        setup.episode_runner.side_effect
    )

    def download(name: str, directory: Path) -> Path:
        if name == "initial":
            assert setup.episode_runner.call_count == 1
            setup.policy.update.assert_not_called()
        return original_download(name, directory)

    def episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if "training" in args[3].parts:
            persisted = json.loads((output / "training.json").read_text())
            assert persisted["initial_checkpoint"]["name"] == "initial"
            assert (
                output / "initial_checkpoint/adapter.safetensors"
            ).read_bytes() == b"initial"
        return original_episode(*args, **kwargs)

    setup.policy.download_checkpoint.side_effect = download
    setup.episode_runner.side_effect = episode
    _, _, evidence, final = training.execute_training(
        setup.prepared, setup.config, "initial-retention"
    )
    assert [
        call.args[0]
        for call in setup.policy.download_checkpoint.call_args_list
    ] == ["initial", "final"]
    assert evidence["initial_checkpoint"]["name"] == "initial"
    assert evidence["checkpoint"]["name"] == "final"
    assert (final / "adapter.safetensors").read_bytes() == b"final"


def test_final_export_failure_retains_completed_evaluation(
    setup: SimpleNamespace,
) -> None:
    """Preserve both evaluations when downloading the final adapter fails.

    Args:
        setup: Isolated training fixture.
    """
    config = setup.config.model_copy(update={"evaluation_attempts": 3})
    original_download: Callable[[str, Path], Path] = (
        setup.policy.download_checkpoint.side_effect
    )

    def download(name: str, directory: Path) -> Path:
        if name == "final":
            raise TimeoutError("checkpoint transfer stalled")
        return original_download(name, directory)

    setup.policy.download_checkpoint.side_effect = download
    with pytest.raises(TimeoutError, match="checkpoint transfer stalled"):
        training.execute_training(setup.prepared, config, "export-failure")
    output = setup.root / "runs/export-failure"
    for phase in ("before", "after"):
        evaluation = json.loads(
            (output / phase / "evaluation.json").read_text()
        )
        assert evaluation["status"] == "completed"
        assert len(evaluation["episodes"]) == 3
        assert evaluation["cleanup"]["complete"] is True
    evidence = json.loads((output / "training.json").read_text())
    assert evidence["status"] == "failed"
    assert evidence["error"]["type"] == "TimeoutError"


def test_connection_resolved_only_after_service_start(
    setup: SimpleNamespace,
) -> None:
    """Use the endpoint assigned during service startup.

    Args:
        setup: Isolated training fixture.
    """

    def credentials() -> tuple[str, str]:
        setup.session.__enter__.assert_called_once()
        return "tml-native-test", "owned.modal.host"

    training.execute_training(
        setup.prepared,
        setup.config,
        "assigned-endpoint",
        client_credentials_factory=credentials,
    )
    arguments = setup.policy_constructor.call_args.kwargs
    assert arguments["api_key"] == "tml-native-test"
    assert arguments["trusted_service_host"] == "owned.modal.host"


@pytest.mark.parametrize("attempts", [0, 21])
def test_evaluation_attempts_are_bounded(
    setup: SimpleNamespace, attempts: int
) -> None:
    """Reject an unbounded evaluation before allocating the service.

    Args:
        setup: Isolated training fixture.
        attempts: Invalid number of attempts per task.
    """
    assert setup.config.evaluation_attempts == 1
    with pytest.raises(ValueError, match="evaluation_attempts"):
        TrainingConfig.model_validate(
            {**setup.config.model_dump(), "evaluation_attempts": attempts}
        )
    setup.service_constructor.assert_not_called()


def test_repeated_evaluations_preserve_snapshots_and_each_attempt(
    setup: SimpleNamespace,
) -> None:
    """Repeat every task with unique paths and retain evidence as attempts finish.

    Args:
        setup: Isolated training fixture.
    """
    config = TrainingConfig.model_validate(
        {**setup.config.model_dump(), "evaluation_attempts": 3}
    )
    setup.prepared["tasks"].append(
        {**setup.prepared["tasks"][0], "task_id": "task-b"}
    )
    setup.rewards[:] = [0, 1, 0, 1, 0, 1]
    original_episode: Callable[..., dict[str, Any]] = (
        setup.episode_runner.side_effect
    )
    completed = {"before": 0, "after": 0}

    def episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output: Path = args[3]
        phase = output.parent.parent.name
        if phase in completed:
            if completed[phase]:
                persisted = json.loads(
                    (output.parent.parent / "evaluation.json").read_text()
                )
                assert len(persisted["episodes"]) == completed[phase]
                assert persisted["status"] == "running"
            completed[phase] += 1
        return original_episode(*args, **kwargs)

    setup.episode_runner.side_effect = episode
    before, after, evidence, _ = training.execute_training(
        setup.prepared, config, "repeated"
    )
    assert completed == {"before": 6, "after": 6}
    assert evidence["optimizer_steps"] == 3
    assert before["protocol"] == after["protocol"]
    assert before["protocol"]["evaluation_attempts"] == 3
    assert before["task_hashes"] == after["task_hashes"]
    calls = setup.episode_runner.call_args_list
    paths = [call.args[3] for call in calls]
    assert len(paths) == len(set(paths)) == 18
    for phase, evaluation, checkpoint in (
        ("before", before, "before"),
        ("after", after, "update-03"),
    ):
        assert [
            (episode["task_id"], episode["attempt_index"])
            for episode in evaluation["episodes"]
        ] == [
            (task, index)
            for task in ("task-a", "task-b")
            for index in range(1, 4)
        ]
        phase_calls = [
            call for call in calls if call.args[3].parent.parent.name == phase
        ]
        assert all(
            call.args[2].samples[0]["checkpoint"] == checkpoint
            for call in phase_calls
        )
        assert [call.args[3].name for call in phase_calls] == [
            "attempt-01",
            "attempt-02",
            "attempt-03",
        ] * 2
        assert evaluation["status"] == "completed"
        assert evaluation["cleanup"]["complete"] is True


@pytest.mark.parametrize("phase", ["before", "after"])
def test_repeated_evaluation_failure_retains_completed_attempts(
    setup: SimpleNamespace,
    phase: str,
) -> None:
    """A later attempt failure leaves earlier results available and cleans up.

    Args:
        setup: Isolated training fixture.
        phase: Evaluation phase that fails after its first attempt.
    """
    config = TrainingConfig.model_validate(
        {**setup.config.model_dump(), "evaluation_attempts": 3}
    )
    original_episode: Callable[..., dict[str, Any]] = (
        setup.episode_runner.side_effect
    )

    def episode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if (
            args[3].name == "attempt-02"
            and args[3].parent.parent.name == phase
        ):
            raise RuntimeError("attempt infrastructure failed")
        return original_episode(*args, **kwargs)

    setup.episode_runner.side_effect = episode
    with pytest.raises(RuntimeError, match="attempt infrastructure failed"):
        training.execute_training(setup.prepared, config, "repeated-failed")
    persisted = json.loads(
        (
            setup.root / "runs/repeated-failed" / phase / "evaluation.json"
        ).read_text()
    )
    assert len(persisted["episodes"]) == 1
    assert persisted["episodes"][0]["attempt_index"] == 1
    assert persisted["status"] == "failed"
    assert persisted["cleanup"]["complete"] is True
    assert persisted["error"]["message"] == "attempt infrastructure failed"
    if phase == "before":
        setup.policy.update.assert_not_called()
    else:
        before = json.loads(
            (
                setup.root / "runs/repeated-failed/before/evaluation.json"
            ).read_text()
        )
        assert before["status"] == "completed"
        assert len(before["episodes"]) == 3
        assert before["cleanup"]["complete"] is True
    setup.session.__exit__.assert_called_once()
    assert setup.session.cleanup_report["complete"] is True


def test_repeated_evaluation_reserve_covers_all_interaction_budgets(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reserve every after attempt plus measured overhead before starting a group.

    Args:
        setup: Isolated training fixture.
        monkeypatch: Scoped patch helper.
    """
    config = TrainingConfig.model_validate(
        {**setup.config.model_dump(), "evaluation_attempts": 10}
    )
    monkeypatch.setattr(time, "monotonic", Mock(side_effect=[0, 200]))
    _, _, evidence, _ = training.execute_training(
        setup.prepared, config, "repeated-reserve"
    )
    assert evidence["paired_evaluation_reserve_seconds"] == (
        10 * config.episode_timeout + 200 + 660
    )
