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
"""Tests for the Harbor campaign steps (skipped when Harbor is missing)."""

from pathlib import Path

import pytest

# Skip on a concrete submodule: without harbor installed, the bare
# "harbor" import can still succeed as an accidental namespace
# package (e.g. this test directory itself on sys.path).
pytest.importorskip("harbor.job")

from zenml.integrations.harbor.models import (  # noqa: E402
    HarborShardResult,
    HarborShardSpec,
    HarborTrialResult,
    TaskRef,
)
from zenml.integrations.harbor.steps import (  # noqa: E402
    build_harbor_matrix,
    build_harbor_report,
    run_harbor_shard,
)

STEPS_MODULE = "zenml.integrations.harbor.steps.harbor_eval_steps"


def test_build_harbor_matrix_expands_local_tasks(tmp_path: Path) -> None:
    """Local tasks are resolved to absolute paths and sharded."""
    task_dir = tmp_path / "hello"
    task_dir.mkdir()
    shards = build_harbor_matrix.entrypoint(
        tasks=[str(task_dir)],
        agents=[{"name": "oracle"}, {"name": "nop"}],
        trials_per_cell=3,
        trials_per_step=2,
    )
    assert len(shards) == 4
    assert all(isinstance(shard, dict) for shard in shards)
    specs = [HarborShardSpec.model_validate(shard) for shard in shards]
    assert {spec.agent_name for spec in specs} == {"oracle", "nop"}
    assert all(spec.task.path == str(task_dir) for spec in specs)


def test_build_harbor_matrix_missing_local_task(tmp_path: Path) -> None:
    """A missing local task fails at matrix time, not shard time."""
    with pytest.raises(FileNotFoundError):
        build_harbor_matrix.entrypoint(tasks=[str(tmp_path / "nope")])


def test_build_harbor_matrix_expands_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dataset specs expand through the Harbor resolver."""
    resolved = [
        TaskRef(
            git_url="https://github.com/org/tasks",
            git_commit_id="deadbeef",
            path=f"tasks/task-{i}",
            source="terminal-bench",
        )
        for i in range(3)
    ]
    captured = {}

    def _fake_resolve(dataset):
        captured["dataset"] = dataset
        return resolved

    monkeypatch.setattr(f"{STEPS_MODULE}.resolve_dataset", _fake_resolve)
    shards = build_harbor_matrix.entrypoint(
        dataset={"name": "terminal-bench", "version": "2.0"},
        agents=[{"name": "oracle"}],
    )
    assert captured["dataset"] == {
        "name": "terminal-bench",
        "version": "2.0",
    }
    assert len(shards) == 3


def test_build_harbor_matrix_requires_tasks() -> None:
    """An empty campaign is rejected."""
    with pytest.raises(ValueError, match="no tasks"):
        build_harbor_matrix.entrypoint(agents=[{"name": "oracle"}])


def _shard_result(n_errored: int = 0) -> HarborShardResult:
    """Build a shard result for step tests."""
    spec = HarborShardSpec(
        shard_id="abc123def456",
        task=TaskRef(path="/tasks/hello"),
        agent_name="oracle",
        trial_indices=[0, 1],
        trial_identities=["identity-0", "identity-1"],
    )
    return HarborShardResult(
        spec=spec,
        job_id="job-1",
        job_name="shard-abc123def456",
        n_total_trials=2,
        n_completed=2 - n_errored,
        n_errored=n_errored,
        n_cancelled=0,
        n_retries=0,
        trials=[
            HarborTrialResult(
                trial_identity="identity-0",
                trial_name="hello__aaaaaaa",
                task_name="hello",
                rewards={"reward": 1.0},
                cost_usd=0.02,
            ),
            HarborTrialResult(
                trial_identity="identity-1",
                trial_name="hello__bbbbbbb",
                task_name="hello",
                rewards={"reward": 0.0},
                cost_usd=0.01,
            ),
        ],
        job_dir="local/jobs/shard-abc123def456",
    )


def test_run_harbor_shard_wires_job_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The step runs the shard job and logs queryable metadata."""
    captured = {}

    def _fake_run_shard_job(spec, jobs_dir, **kwargs):
        captured["spec"] = spec
        captured["jobs_dir"] = jobs_dir
        captured["kwargs"] = kwargs
        return _shard_result()

    def _fake_log_metadata(metadata):
        captured["metadata"] = metadata

    monkeypatch.setattr(f"{STEPS_MODULE}.run_shard_job", _fake_run_shard_job)
    monkeypatch.setattr(f"{STEPS_MODULE}.log_metadata", _fake_log_metadata)

    shard = _shard_result().spec.model_dump(mode="json")
    result = run_harbor_shard.entrypoint(shard=shard, n_concurrent_trials=2)

    assert isinstance(result, HarborShardResult)
    assert captured["spec"].shard_id == "abc123def456"
    assert captured["jobs_dir"].exists()
    assert captured["kwargs"]["n_concurrent_trials"] == 2
    metadata = captured["metadata"]
    assert metadata["harbor.shard_id"] == "abc123def456"
    assert metadata["harbor.task"] == "hello"
    assert metadata["harbor.agent"] == "oracle"
    assert metadata["harbor.n_trials"] == 2
    assert metadata["harbor.n_completed"] == 2
    assert metadata["harbor.n_errored"] == 0
    assert metadata["harbor.mean_reward"] == 0.5
    assert metadata["harbor.cost_usd"] == pytest.approx(0.03)


def test_run_harbor_shard_fail_on_trial_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With fail_on_trial_error, errored trials fail the step.

    The shard result must be rescued as a manual artifact before the
    raise — otherwise the job archive (the logs needed to debug the
    errored trials) would be lost with the failed step.
    """
    monkeypatch.setattr(
        f"{STEPS_MODULE}.run_shard_job",
        lambda **kwargs: _shard_result(n_errored=1),
    )
    monkeypatch.setattr(f"{STEPS_MODULE}.log_metadata", lambda metadata: None)
    rescued = {}

    def _fake_save_artifact(data, name, materializer=None):
        rescued["data"] = data
        rescued["name"] = name

    monkeypatch.setattr(f"{STEPS_MODULE}.save_artifact", _fake_save_artifact)
    shard = _shard_result().spec.model_dump(mode="json")

    with pytest.raises(RuntimeError, match="errored"):
        run_harbor_shard.entrypoint(shard=shard, fail_on_trial_error=True)
    assert rescued["name"] == "harbor_shard_result_abc123def456_failed"
    assert rescued["data"].n_errored == 1

    # Without the flag, errored trials are a result, not a failure.
    rescued.clear()
    result = run_harbor_shard.entrypoint(shard=shard)
    assert result.n_errored == 1
    assert not rescued


def test_run_harbor_shard_pins_its_materializer() -> None:
    """The shard step must not rely on integration activation.

    `activate()` is skipped whenever `check_installation()` finds any
    transitive requirement out of range, which would silently fall back
    to PydanticMaterializer and drop the job archive.
    """
    from zenml.integrations.harbor.materializers import (
        HarborShardResultMaterializer,
    )

    materializer_sources = run_harbor_shard.configuration.outputs[
        "harbor_shard_result"
    ].materializer_source
    assert materializer_sources
    assert any(
        source.attribute == HarborShardResultMaterializer.__name__
        for source in materializer_sources
    )


def test_build_harbor_report_aggregates_cells() -> None:
    """The report has one row per cell plus totals."""
    report = build_harbor_report.entrypoint(
        results=[_shard_result(), _shard_result()]
    )
    assert "# Harbor campaign report" in report
    assert "4 trial(s) in 2 shard(s)" in report
    assert "| hello | oracle | n/a | 4 | 4 | 0 | reward=0.500 | 0.0600 |" in (
        report
    )
    assert "**Total**" in report
