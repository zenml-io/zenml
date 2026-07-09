#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for the Harbor job runner (skipped when Harbor is missing)."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

# Skip on a concrete submodule: without harbor installed, the bare
# "harbor" import can still succeed as an accidental namespace
# package (e.g. this test directory itself on sys.path).
pytest.importorskip("harbor.job")

from zenml.integrations.harbor import (  # noqa: E402
    ZENML_HARBOR_ENV_IMPORT_PATH,
)
from zenml.integrations.harbor.job_runner import (  # noqa: E402
    build_job_config,
    run_shard_job,
)
from zenml.integrations.harbor.models import (  # noqa: E402
    HarborShardSpec,
    TaskRef,
)


def test_harbor_api_canary() -> None:
    """Every Harbor symbol the integration touches still exists.

    A Harbor version bump that breaks this test would otherwise only
    fail at user runtime.
    """
    import inspect

    from harbor.environments.base import (
        BaseEnvironment,
        ExecResult,
    )
    from harbor.job import Job
    from harbor.models.job.config import (
        DatasetConfig,
        JobConfig,
        RetryConfig,
    )
    from harbor.models.job.result import JobResult, JobStats
    from harbor.models.task.config import (
        EnvironmentConfig as TaskEnvironmentConfig,
    )
    from harbor.models.task.task import Task
    from harbor.models.trial.config import (
        AgentConfig,
        EnvironmentConfig,
        TaskConfig,
        VerifierConfig,
    )
    from harbor.models.trial.paths import EnvironmentPaths
    from harbor.models.trial.result import TrialResult
    from harbor.models.verifier.result import VerifierResult

    assert callable(Job.create)
    assert callable(DatasetConfig.get_task_configs)
    assert (
        "disable_verification"
        in inspect.signature(DatasetConfig.get_task_configs).parameters
    )
    assert callable(EnvironmentPaths.for_os)
    assert isinstance(Task.has_steps, property)
    for field in ("job_name", "jobs_dir", "n_attempts", "quiet", "retry"):
        assert field in JobConfig.model_fields
    for field in ("name", "model_name", "kwargs", "env"):
        assert field in AgentConfig.model_fields
    for field in (
        "path",
        "git_url",
        "git_commit_id",
        "name",
        "ref",
        "source",
    ):
        assert field in TaskConfig.model_fields
    assert "import_path" in EnvironmentConfig.model_fields
    assert "trial_results" in JobResult.model_fields
    assert "disable" in VerifierConfig.model_fields
    assert "max_retries" in RetryConfig.model_fields
    for method in ("start", "stop", "exec", "upload_file", "download_file"):
        assert method in BaseEnvironment.__abstractmethods__
    assert "return_code" in ExecResult.model_fields
    # Result-side surface consumed by HarborTrialResult.from_harbor and
    # run_shard_job — the shapes the SimpleNamespace mocks fabricate.
    for field in (
        "trial_name",
        "task_name",
        "source",
        "task_checksum",
        "step_results",
        "agent_info",
        "verifier_result",
        "exception_info",
        "started_at",
        "finished_at",
    ):
        assert field in TrialResult.model_fields
    assert callable(TrialResult.compute_token_cost_totals)
    assert "rewards" in VerifierResult.model_fields
    for field in (
        "n_completed_trials",
        "n_errored_trials",
        "n_cancelled_trials",
        "n_retries",
    ):
        assert field in JobStats.model_fields
    # Environment-side surface consumed by the Sandbox bridge.
    for field in (
        "docker_image",
        "allow_internet",
        "cpus",
        "memory_mb",
        "gpus",
        "os",
    ):
        assert field in TaskEnvironmentConfig.model_fields


def test_resolve_dataset_maps_task_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harbor TaskConfigs map field-by-field onto TaskRefs."""
    from pathlib import Path as _Path

    from harbor.models.job.config import DatasetConfig
    from harbor.models.trial.config import TaskConfig

    from zenml.integrations.harbor.job_runner import resolve_dataset

    captured = {}

    async def _fake_get_task_configs(self, disable_verification=False):
        captured["disable_verification"] = disable_verification
        captured["name"] = self.name
        # Harbor's TaskConfig forbids setting both `path` and `name`.
        return [
            TaskConfig(
                git_url="https://github.com/org/tasks",
                git_commit_id="deadbeef",
                path=_Path("tasks/chess"),
                source="terminal-bench",
            ),
            TaskConfig(path=_Path("/local/task")),
        ]

    monkeypatch.setattr(
        DatasetConfig, "get_task_configs", _fake_get_task_configs
    )
    refs = resolve_dataset({"name": "terminal-bench", "version": "2.0"})

    assert captured["disable_verification"] is True
    assert captured["name"] == "terminal-bench"
    assert refs[0].git_url == "https://github.com/org/tasks"
    assert refs[0].git_commit_id == "deadbeef"
    assert refs[0].path == "tasks/chess"
    assert refs[0].name is None
    assert refs[0].source == "terminal-bench"
    assert refs[1].path == "/local/task"
    assert refs[1].git_url is None


def test_resolve_dataset_rejects_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dataset resolving to no tasks is an error."""
    from harbor.models.job.config import DatasetConfig

    from zenml.integrations.harbor.job_runner import resolve_dataset

    async def _empty(self, disable_verification=False):
        return []

    monkeypatch.setattr(DatasetConfig, "get_task_configs", _empty)
    with pytest.raises(ValueError, match="no tasks"):
        resolve_dataset({"name": "empty-set"})


def _spec(task: TaskRef = None, n_trials: int = 2) -> HarborShardSpec:
    """Build a shard spec for the given task."""
    return HarborShardSpec(
        shard_id="abc123def456ghi",
        task=task or TaskRef(path="/tasks/hello"),
        agent_name="oracle",
        model_name="claude-fable-5",
        agent_kwargs={"budget": 1},
        agent_env={"KEY": "value"},
        trial_indices=list(range(n_trials)),
        trial_identities=[f"identity-{i}" for i in range(n_trials)],
    )


def _write_task_dir(tmp_path: Path) -> Path:
    """Write a minimal loadable Harbor task directory."""
    task_dir = tmp_path / "hello"
    (task_dir / "tests").mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        'schema_version = "1.2"\n\n[metadata]\n\n[verifier]\n\n'
        "[agent]\n\n[environment]\n"
    )
    (task_dir / "instruction.md").write_text("Write 42 to /app/answer.txt")
    (task_dir / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n")
    return task_dir


def test_build_job_config_maps_shard_onto_single_cell_job(
    tmp_path: Path,
) -> None:
    """The shard translates 1:1 into a single-task single-agent job."""
    task_dir = _write_task_dir(tmp_path)
    spec = _spec(task=TaskRef(path=str(task_dir)))

    config = build_job_config(
        spec=spec, jobs_dir=tmp_path / "jobs", n_concurrent_trials=8
    )

    assert config.job_name == "shard-abc123def456"
    assert config.n_attempts == 2
    # Concurrency never exceeds the shard size.
    assert config.n_concurrent_trials == 2
    assert config.quiet is True
    assert len(config.tasks) == 1
    assert config.tasks[0].path == task_dir
    assert len(config.agents) == 1
    assert config.agents[0].name == "oracle"
    assert config.agents[0].model_name == "claude-fable-5"
    assert config.agents[0].kwargs == {"budget": 1}
    assert config.agents[0].env == {"KEY": "value"}
    assert config.environment.import_path == ZENML_HARBOR_ENV_IMPORT_PATH
    assert config.retry.max_retries == 0


def test_build_job_config_git_task(tmp_path: Path) -> None:
    """Git-pinned tasks pass through with their commit pin.

    The dataset `source` must NOT reach the Harbor job config: shards
    resolve datasets client-side, and a sourced trial crashes Harbor
    0.8's quiet-mode progress display (IndexError on the missing
    dataset metric bucket).
    """
    spec = _spec(
        task=TaskRef(
            git_url="https://github.com/org/tasks",
            git_commit_id="deadbeef",
            path="tasks/chess",
            source="terminal-bench",
        )
    )
    config = build_job_config(spec=spec, jobs_dir=tmp_path)
    assert config.tasks[0].git_url == "https://github.com/org/tasks"
    assert config.tasks[0].git_commit_id == "deadbeef"
    assert config.tasks[0].path == Path("tasks/chess")
    assert config.tasks[0].source is None


def test_build_job_config_missing_local_task(tmp_path: Path) -> None:
    """A missing local task directory fails fast."""
    spec = _spec(task=TaskRef(path=str(tmp_path / "nope")))
    with pytest.raises(FileNotFoundError):
        build_job_config(spec=spec, jobs_dir=tmp_path)


def test_build_job_config_rejects_multi_step_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local multi-step tasks are rejected before the job starts."""
    task_dir = tmp_path / "multi"
    task_dir.mkdir()
    monkeypatch.setattr(
        "zenml.integrations.harbor.job_runner.Task",
        lambda _: SimpleNamespace(has_steps=True),
    )
    spec = _spec(task=TaskRef(path=str(task_dir)))
    with pytest.raises(NotImplementedError, match="multi-step"):
        build_job_config(spec=spec, jobs_dir=tmp_path)


def test_run_shard_job_assembles_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The in-memory JobResult is turned into a shard result."""
    task_dir = tmp_path / "hello"
    task_dir.mkdir()
    monkeypatch.setattr(
        "zenml.integrations.harbor.job_runner.Task",
        lambda _: SimpleNamespace(has_steps=False),
    )

    def _trial(name: str, reward: float) -> SimpleNamespace:
        return SimpleNamespace(
            trial_name=name,
            task_name="hello",
            source=None,
            task_checksum="sha256-of-task",
            step_results=None,
            agent_info=SimpleNamespace(name="oracle", model_info=None),
            verifier_result=SimpleNamespace(rewards={"reward": reward}),
            exception_info=None,
            compute_token_cost_totals=lambda: (None, None, None, None),
            started_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            finished_at=None,
        )

    job_result = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        n_total_trials=2,
        stats=SimpleNamespace(
            n_completed_trials=2,
            n_errored_trials=0,
            n_cancelled_trials=0,
            n_retries=1,
        ),
        trial_results=[
            _trial("hello__aaaaaaa", 1.0),
            _trial("hello__bbbbbbb", 0.0),
        ],
    )
    captured = {}

    class _FakeJob:
        @classmethod
        async def create(cls, config):
            captured["config"] = config
            return cls()

        async def run(self):
            return job_result

    monkeypatch.setattr("zenml.integrations.harbor.job_runner.Job", _FakeJob)

    # The bridge records sandbox facts at session start, keyed by the
    # trial name; the runner stamps them onto the matching trial only.
    from zenml.integrations.harbor.environment import (
        SandboxProvenance,
        _session_provenance,
    )

    _session_provenance["hello__aaaaaaa"] = SandboxProvenance(
        flavor="modal", docker_image="python:3.11-slim"
    )

    spec = _spec(
        task=TaskRef(path=str(task_dir), source="terminal-bench-sample")
    )
    result = run_shard_job(spec=spec, jobs_dir=tmp_path / "jobs")

    # Dataset provenance is restored even though build_job_config
    # strips it from the Harbor-side task config.
    assert all(t.source == "terminal-bench-sample" for t in result.trials)
    assert result.trials[0].task_checksum == "sha256-of-task"
    assert result.trials[0].sandbox_flavor == "modal"
    assert result.trials[0].sandbox_docker_image == "python:3.11-slim"
    assert result.trials[1].sandbox_flavor is None
    # The runner drained the provenance registry.
    assert "hello__aaaaaaa" not in _session_provenance

    assert captured["config"].n_attempts == 2
    assert result.job_id == "00000000-0000-0000-0000-000000000001"
    assert result.job_name == "shard-abc123def456"
    assert result.n_completed == 2
    assert result.n_retries == 1
    assert result.job_dir == str(tmp_path / "jobs" / "shard-abc123def456")
    # Trials pair with the precomputed identities by encounter order.
    assert [t.trial_identity for t in result.trials] == [
        "identity-0",
        "identity-1",
    ]
    assert result.trials[0].rewards == {"reward": 1.0}
    assert result.trials[1].rewards == {"reward": 0.0}
    assert result.mean_reward == {"reward": 0.5}
