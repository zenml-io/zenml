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
"""Tests for the Harbor campaign models (no Harbor required)."""

import tarfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from zenml.integrations.harbor.models import (
    HarborShardResult,
    HarborShardSpec,
    HarborTrialResult,
    TaskRef,
)


def _shard_spec(**kwargs) -> HarborShardSpec:
    """Build a minimal shard spec for tests."""
    defaults = dict(
        shard_id="abc123",
        task=TaskRef(path="/tasks/hello"),
        agent_name="oracle",
        trial_indices=[0, 1],
        trial_identities=["id-0", "id-1"],
    )
    defaults.update(kwargs)
    return HarborShardSpec(**defaults)


def _harbor_trial_result(**kwargs) -> SimpleNamespace:
    """Mimic a harbor TrialResult with the attributes `from_harbor` reads."""
    defaults = dict(
        trial_name="hello__abc1234",
        task_name="hello",
        source="terminal-bench",
        task_checksum="sha256-of-task",
        step_results=None,
        agent_info=SimpleNamespace(
            name="oracle", model_info=SimpleNamespace(name="gpt-x")
        ),
        verifier_result=SimpleNamespace(rewards={"reward": 1}),
        exception_info=None,
        compute_token_cost_totals=lambda: (10, 2, 5, 0.01),
        started_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 1, 0, 5, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_task_ref_git_round_trip() -> None:
    """Git-pinned refs survive parse -> to_string unchanged."""
    spec = "git+https://github.com/org/tasks@deadbeef:tasks/chess"
    ref = TaskRef.parse(spec)
    assert ref.git_url == "https://github.com/org/tasks"
    assert ref.git_commit_id == "deadbeef"
    assert ref.path == "tasks/chess"
    assert ref.to_string() == spec
    assert ref.display_name == "chess"


@pytest.mark.parametrize(
    "bad_spec",
    [
        # No @COMMIT pin at all.
        "git+https://github.com/org/tasks:tasks/chess",
        # ssh userinfo '@' would be misparsed as the pin separator.
        "git+git@github.com:org/tasks.git",
        # Empty URL.
        "git+@deadbeef:tasks/chess",
    ],
)
def test_task_ref_rejects_malformed_git_specs(bad_spec: str) -> None:
    """Malformed git+ specs fail at parse time, not at clone time."""
    with pytest.raises(ValueError, match="Invalid git task ref"):
        TaskRef.parse(bad_spec)


def test_task_ref_local_round_trip() -> None:
    """Local path refs survive parse -> to_string unchanged."""
    ref = TaskRef.parse("tasks/hello")
    assert ref.path == "tasks/hello"
    assert ref.git_url is None
    assert ref.to_string() == "tasks/hello"
    assert ref.display_name == "hello"


def test_trial_result_from_harbor() -> None:
    """All flat fields are extracted from a harbor TrialResult."""
    result = HarborTrialResult.from_harbor(
        _harbor_trial_result(), trial_identity="identity-0"
    )
    assert result.trial_identity == "identity-0"
    assert result.trial_name == "hello__abc1234"
    assert result.task_name == "hello"
    assert result.source == "terminal-bench"
    assert result.task_checksum == "sha256-of-task"
    # Sandbox provenance is stamped by the shard runner, not here.
    assert result.sandbox_flavor is None
    assert result.sandbox_docker_image is None
    assert result.agent_name == "oracle"
    assert result.model_name == "gpt-x"
    assert result.rewards == {"reward": 1.0}
    assert result.exception_type is None
    assert result.n_input_tokens == 10
    assert result.n_cache_tokens == 2
    assert result.n_output_tokens == 5
    assert result.cost_usd == 0.01


def test_trial_result_from_harbor_with_exception() -> None:
    """Errored trials carry their exception info, not rewards."""
    result = HarborTrialResult.from_harbor(
        _harbor_trial_result(
            verifier_result=None,
            exception_info=SimpleNamespace(
                exception_type="TimeoutError",
                exception_message="agent timed out",
            ),
        ),
        trial_identity="identity-0",
    )
    assert result.rewards is None
    assert result.exception_type == "TimeoutError"
    assert result.exception_message == "agent timed out"


def test_trial_result_from_harbor_rejects_multi_step() -> None:
    """Multi-step trials are rejected loudly."""
    with pytest.raises(NotImplementedError, match="multi-step"):
        HarborTrialResult.from_harbor(
            _harbor_trial_result(step_results=[SimpleNamespace()]),
            trial_identity="identity-0",
        )


def _shard_result(trials, **kwargs) -> HarborShardResult:
    """Build a shard result around the given trials."""
    defaults = dict(
        spec=_shard_spec(),
        job_id="job-1",
        job_name="shard-abc123",
        n_total_trials=len(trials),
        n_completed=len(trials),
        n_errored=0,
        n_cancelled=0,
        n_retries=0,
        trials=trials,
    )
    defaults.update(kwargs)
    return HarborShardResult(**defaults)


def _trial(identity: str, rewards=None, cost=None) -> HarborTrialResult:
    """Build a flat trial result."""
    return HarborTrialResult(
        trial_identity=identity,
        trial_name=f"hello__{identity}",
        task_name="hello",
        rewards=rewards,
        cost_usd=cost,
    )


def test_shard_result_mean_reward_and_cost() -> None:
    """Aggregates average per reward key and sum costs."""
    result = _shard_result(
        [
            _trial("a", rewards={"reward": 1.0}, cost=0.02),
            _trial("b", rewards={"reward": 0.0}, cost=0.03),
            _trial("c"),
        ]
    )
    assert result.mean_reward == {"reward": 0.5}
    assert result.total_cost_usd == pytest.approx(0.05)


def test_shard_result_mean_reward_none_when_unscored() -> None:
    """No scored trial means no mean reward."""
    result = _shard_result([_trial("a"), _trial("b")])
    assert result.mean_reward is None
    assert result.total_cost_usd is None


def test_shard_result_n_succeeded_excludes_errored() -> None:
    """Harbor counts errored trials as completed; n_succeeded must not."""
    result = _shard_result(
        [_trial("a"), _trial("b")], n_completed=2, n_errored=2
    )
    assert result.n_succeeded == 0
    result = _shard_result(
        [_trial("a"), _trial("b")], n_completed=2, n_errored=1
    )
    assert result.n_succeeded == 1


def test_shard_result_json_round_trip_excludes_transient_fields() -> None:
    """job_dir and archive_uri never enter the serialized form."""
    result = _shard_result(
        [_trial("a", rewards={"reward": 1.0})],
        job_dir="local/job-dir",
        archive_uri="s3://bucket/archive.tar.gz",
    )
    dumped = result.model_dump_json()
    assert "job_dir" not in dumped
    assert "archive_uri" not in dumped
    restored = HarborShardResult.model_validate_json(dumped)
    assert restored.job_dir is None
    assert restored.archive_uri is None
    assert restored.trials == result.trials
    assert restored.spec == result.spec


def test_download_jobs_dir_extracts_archive(tmp_path: Path) -> None:
    """The archived job tree is restored on demand."""
    job_dir = tmp_path / "job"
    (job_dir / "trial-1").mkdir(parents=True)
    (job_dir / "trial-1" / "result.json").write_text("{}")
    archive = tmp_path / "job_dir.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(job_dir, arcname=".")

    result = _shard_result([], archive_uri=str(archive))
    target = result.download_jobs_dir(tmp_path / "restored")
    assert (target / "trial-1" / "result.json").read_text() == "{}"
    assert not (target / "job_dir.tar.gz").exists()


def test_download_jobs_dir_skips_traversal_members(tmp_path: Path) -> None:
    """Path-traversal members in the archive are not extracted."""
    payload = tmp_path / "payload.txt"
    payload.write_text("evil")
    archive = tmp_path / "job_dir.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(payload, arcname="../escaped.txt")
        tar.add(payload, arcname="safe.txt")

    result = _shard_result([], archive_uri=str(archive))
    target = result.download_jobs_dir(tmp_path / "restored")
    assert (target / "safe.txt").exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_download_jobs_dir_requires_archive_uri() -> None:
    """Without an archive reference, downloading fails clearly."""
    result = _shard_result([])
    with pytest.raises(RuntimeError, match="no job archive"):
        result.download_jobs_dir("anywhere")
