"""Cloud lifecycle ownership and failure-path checks without cloud access."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from cloud import KubernetesInference


@pytest.fixture
def session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> KubernetesInference:
    """Build a session using fake executable paths.

    Args:
        tmp_path: Evidence directory supplied by pytest.
        monkeypatch: Scoped patch helper.

    Returns:
        A configured session that has made no cloud calls.
    """
    monkeypatch.setattr("shutil.which", lambda name: "/fake/" + name)
    return KubernetesInference(
        {
            "aws_profile": "test",
            "aws_region": "test-region",
            "kube_context": "test-context",
            "namespace": "test-namespace",
            "gpu_asg": "test-group",
            "vllm_image": "vllm@sha256:" + "a" * 64,
        },
        {"name": "model", "revision": "b" * 40},
        "test-run",
        tmp_path,
    )


def test_collision_does_not_delete_or_terminate(
    session: KubernetesInference,
) -> None:
    """A same-name job owned by someone else prevents any destructive call.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session._job = Mock(  # type: ignore[method-assign]
        return_value={
            "metadata": {"uid": "other", "labels": {"endless-owner": "other"}}
        }
    )
    session._kube = Mock(return_value="logs")  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="ownership token"):
        session._cleanup()
    session._gpu_cleanup.assert_not_called()
    assert all(
        call.args[0] != "delete" for call in session._kube.call_args_list
    )


def test_log_failure_does_not_prevent_cleanup(
    session: KubernetesInference,
) -> None:
    """Diagnostics cannot prevent job deletion or worker termination.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session._kube = Mock(side_effect=RuntimeError("logs unavailable"))  # type: ignore[method-assign]
    session._delete_job = Mock()  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    session._cleanup()
    session._delete_job.assert_called_once()
    session._gpu_cleanup.assert_called_once()
    assert session.cleanup_report["complete"]
    assert "logs unavailable" in session.cleanup_report["diagnostic_error"]


def test_cleanup_failure_propagates(session: KubernetesInference) -> None:
    """An incomplete teardown is never reported as a successful session.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session._kube = Mock(return_value="logs")  # type: ignore[method-assign]
    session._delete_job = Mock()  # type: ignore[method-assign]
    session._gpu_cleanup = Mock(side_effect=RuntimeError("instance remains"))  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="instance remains"):
        session.__exit__(None, None, None)
    assert not session.cleanup_report["complete"]


def test_forward_failure_does_not_skip_worker_cleanup(
    session: KubernetesInference,
) -> None:
    """Port-forward shutdown and GPU cleanup fail independently.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session.forward = Mock()
    session._stop = Mock(side_effect=RuntimeError("forward stuck"))  # type: ignore[method-assign]
    session._kube = Mock(return_value="logs")  # type: ignore[method-assign]
    session._delete_job = Mock()  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="forward stuck"):
        session._cleanup()
    session._gpu_cleanup.assert_called_once()


def test_delete_has_uid_precondition(session: KubernetesInference) -> None:
    """The API receives a UID precondition protecting replacement jobs.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    import json

    session._job = Mock(  # type: ignore[method-assign]
        side_effect=[
            {
                "metadata": {
                    "uid": "owned-uid",
                    "labels": {"endless-owner": session.token},
                }
            },
            None,
        ]
    )
    session._pods = Mock(return_value=[])  # type: ignore[method-assign]
    session._kube = Mock(return_value="")  # type: ignore[method-assign]
    session._delete_job()
    body = json.loads((session.directory / "delete-options.json").read_text())
    assert body["preconditions"] == {"uid": "owned-uid"}
    assert session._kube.call_args.args[:2] == ("delete", "--raw")


def test_remaining_serving_time_includes_startup(
    session: KubernetesInference, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup consumes the same finite lifetime as episode execution.

    Args:
        session: Isolated cloud session with mocked operations.
        monkeypatch: Scoped clock patch helper.
    """
    assert session.serving_seconds_remaining == 0
    session._serving_deadline = 2700.0
    monkeypatch.setattr("cloud.time.monotonic", lambda: 900.0)
    assert session.serving_seconds_remaining == 1800.0
    monkeypatch.setattr("cloud.time.monotonic", lambda: 2800.0)
    assert session.serving_seconds_remaining == 0


def test_manifest_supports_tainted_gpu_nodes_and_shared_memory(
    session: KubernetesInference,
) -> None:
    """Serving can schedule on the GPU pool with sufficient shared memory.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    pod = session._manifest()["spec"]["template"]["spec"]
    assert pod["tolerations"] == [
        {
            "key": "pool",
            "operator": "Equal",
            "value": "gpu",
            "effect": "NoSchedule",
        }
    ]
    assert pod["volumes"] == [
        {"name": "shm", "emptyDir": {"medium": "Memory", "sizeLimit": "2Gi"}}
    ]
    container = pod["containers"][0]
    assert container["volumeMounts"] == [
        {"name": "shm", "mountPath": "/dev/shm"}
    ]
    assert "--disable-log-requests" in container["args"]
    assert container["readinessProbe"]["exec"]["command"][0] == "python3"
    session.config["tolerations"] = []
    assert session._manifest()["spec"]["template"]["spec"]["tolerations"] == []


def test_skyrl_manifest_uses_training_entrypoint(
    session: KubernetesInference,
) -> None:
    """SkyRL receives pinned weights through its own entrypoint.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    config = {
        **session.config,
        "server_kind": "skyrl",
        "training_image": "trainer@sha256:" + "c" * 64,
    }
    del config["vllm_image"]
    training = KubernetesInference(
        config, session.model, "training", session.directory
    )
    container = training._manifest()["spec"]["template"]["spec"]["containers"][
        0
    ]
    assert container["image"] == config["training_image"]
    assert "args" not in container
    assert container["env"] == [
        {"name": "SKYRL_MODEL_NAME", "value": "model"},
        {"name": "SKYRL_DUMP_INFRA_LOG_TO_STDOUT", "value": "1"},
        {
            "name": "RAY_DEFAULT_OBJECT_STORE_MAX_MEMORY_BYTES",
            "value": "1073741824",
        },
        {"name": "SKYRL_MODEL_REVISION", "value": "b" * 40},
    ]
    assert (
        "/api/v1/healthz" in container["readinessProbe"]["exec"]["command"][-1]
    )
    assert training.identity["server_kind"] == "skyrl"
    config["training_image"] = "trainer:latest"
    with pytest.raises(ValueError, match="training_image"):
        KubernetesInference(
            config, session.model, "training", session.directory
        )


def test_skyrl_checks_downloaded_model_identity(
    session: KubernetesInference, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Healthy API with the wrong downloaded weights is rejected.

    Args:
        session: Isolated cloud session with mocked operations.
        monkeypatch: Scoped HTTP patch helper.
    """
    import json
    from unittest.mock import MagicMock

    session.server_kind = "skyrl"
    session.base_url = "http://127.0.0.1:8000"
    monkeypatch.setattr("cloud.urllib.request.urlopen", MagicMock())
    session._kube = Mock(  # type: ignore[method-assign]
        return_value=json.dumps(
            {
                "model_name": "model",
                "model_revision": "wrong",
            }
        )
    )
    with pytest.raises(RuntimeError, match="model identity mismatch"):
        session._verify_server()
    session._kube = Mock(  # type: ignore[method-assign]
        return_value=json.dumps(
            {
                "model_name": "model",
                "model_revision": "b" * 40,
            }
        )
    )
    session._verify_server()
    assert session.identity["training_server"]["model_revision"] == "b" * 40


def test_skyrl_worker_diagnostic_failure_does_not_block_cleanup(
    session: KubernetesInference,
) -> None:
    """A timed-out worker-log capture must still delete the job and GPU worker.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session.server_kind = "skyrl"
    session._kube = Mock(return_value="API logs")  # type: ignore[method-assign]
    session._capture_training_logs = Mock(  # type: ignore[method-assign]
        side_effect=TimeoutError("diagnostic deadline")
    )
    session._delete_job = Mock()  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    session._cleanup()
    session._delete_job.assert_called_once()
    session._gpu_cleanup.assert_called_once()
    assert session.cleanup_report["complete"] is True
    assert (
        "diagnostic deadline"
        in session.cleanup_report["training_diagnostic_error"]
    )


def test_worker_diagnostics_are_bounded_and_captured_before_delete(
    session: KubernetesInference,
) -> None:
    """Collect owned SkyRL log tails before any destructive cleanup operation.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session.server_kind = "skyrl"
    session._job = Mock(  # type: ignore[method-assign]
        return_value={
            "metadata": {
                "uid": "owned",
                "labels": {"endless-owner": session.token},
            }
        }
    )
    session._kube = Mock(return_value="API logs")  # type: ignore[method-assign]
    session._call = Mock(return_value='{"log_tails": {}}')  # type: ignore[method-assign]

    def delete() -> None:
        assert (session.directory / "training-worker-logs.json").exists()

    session._delete_job = Mock(side_effect=delete)  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    session._cleanup()
    assert session._call.call_args.kwargs["timeout"] == 20
    command = session._call.call_args.args[0]
    assert command[-3:-1] == ["python3", "-c"]
    assert "/tmp/skyrl-logs" in command[-1]
    assert "/tmp/ray/session_latest/logs" in command[-1]
    assert "65536" in command[-1]
    session._delete_job.assert_called_once()


def test_vllm_cleanup_does_not_request_worker_files(
    session: KubernetesInference,
) -> None:
    """Keep ordinary vLLM cleanup independent of SkyRL's filesystem layout.

    Args:
        session: Isolated cloud session with mocked operations.
    """
    session.attempted = True
    session._kube = Mock(return_value="API logs")  # type: ignore[method-assign]
    session._capture_training_logs = Mock()  # type: ignore[method-assign]
    session._delete_job = Mock()  # type: ignore[method-assign]
    session._gpu_cleanup = Mock()  # type: ignore[method-assign]
    session._cleanup()
    session._capture_training_logs.assert_not_called()


def test_remote_collector_retains_memory_and_actor_death_evidence(
    session: KubernetesInference,
    tmp_path: Path,
) -> None:
    """Run the collector locally with enough worker logs to crowd out diagnostics.

    Args:
        session: Isolated cloud session with mocked operations.
        tmp_path: Temporary stand-in for remote logs and cgroup files.
    """
    import json
    import subprocess
    import sys

    ray = tmp_path / "ray"
    ray.mkdir()
    cgroup = tmp_path / "cgroup"
    cgroup.mkdir()
    critical = ["raylet.out", "raylet.err", "gcs_server.out", "gcs_server.err"]
    for name in critical:
        (ray / name).write_text(
            "Actor died: worker killed by memory monitor\n"
        )
    for index in range(30):
        (ray / f"python-core-worker-{index:02d}.log").write_text(
            "ordinary worker output\n"
        )
    for name in (
        "memory.events",
        "memory.current",
        "memory.peak",
        "memory.max",
    ):
        (cgroup / name).write_text(
            "oom_kill 1\n" if name == "memory.events" else "1073741824\n"
        )
    session._job = Mock(  # type: ignore[method-assign]
        return_value={
            "metadata": {
                "uid": "owned",
                "labels": {"endless-owner": session.token},
            }
        }
    )
    session._call = Mock(return_value="{}")  # type: ignore[method-assign]
    session._capture_training_logs()
    script = session._call.call_args.args[0][-1]
    script = script.replace("/tmp/skyrl-logs", str(tmp_path / "absent"))
    script = script.replace("/tmp/ray/session_latest/logs", str(ray))
    script = script.replace("/sys/fs/cgroup", str(cgroup))
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    logs = json.loads(completed.stdout)["log_tails"]
    assert all(str(ray / name) in logs for name in critical)
    assert "Actor died" in logs[str(ray / "gcs_server.out")]
    assert logs[str(cgroup / "memory.events")] == "oom_kill 1\n"
    assert len(logs) <= 20
    assert sum(len(value.encode()) for value in logs.values()) <= 1048576
