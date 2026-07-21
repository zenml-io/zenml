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
"""Tests for the Harbor shard-result materializer (no Harbor required)."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from tests.unit.test_general import _test_materializer

from zenml.integrations.harbor.materializers import (
    HarborShardResultMaterializer,
)
from zenml.integrations.harbor.models import (
    HarborShardResult,
    HarborShardSpec,
    HarborTrialResult,
    TaskRef,
)


def _shard_result(job_dir: str = None) -> HarborShardResult:
    """Build a shard result, optionally referencing a local job dir."""
    return HarborShardResult(
        spec=HarborShardSpec(
            shard_id="abc123def456",
            task=TaskRef(path="/tasks/hello"),
            agent_name="oracle",
            model_name="claude-fable-5",
            trial_indices=[0],
            trial_identities=["identity-0"],
        ),
        job_id="job-1",
        job_name="shard-abc123def456",
        n_total_trials=1,
        n_completed=1,
        n_errored=0,
        n_cancelled=0,
        n_retries=0,
        trials=[
            HarborTrialResult(
                trial_identity="identity-0",
                trial_name="hello__abc1234",
                task_name="hello",
                rewards={"reward": 1.0},
                cost_usd=0.01,
            )
        ],
        job_dir=job_dir,
    )


def test_materializer_round_trip_without_job_dir() -> None:
    """A result without a job dir round-trips with no archive."""
    result = _test_materializer(
        step_output=_shard_result(),
        materializer_class=HarborShardResultMaterializer,
        assert_visualization_exists=True,
    )
    assert result.trials[0].rewards == {"reward": 1.0}
    assert result.archive_uri is None
    assert result.job_dir is None


def test_materializer_archives_job_dir(tmp_path: Path) -> None:
    """A live job dir is archived and restorable after load."""
    job_dir = tmp_path / "shard-abc123def456"
    (job_dir / "trial-1" / "agent").mkdir(parents=True)
    (job_dir / "trial-1" / "result.json").write_text('{"ok": true}')

    # Manual save/load against a persistent URI (unlike
    # `_test_materializer`, which deletes its URI on exit) so the
    # archive is still there when `download_jobs_dir` fetches it.
    from zenml.client import Client

    artifact_uri = os.path.join(
        Client().active_stack.artifact_store.path,
        f"harbor-materializer-test-{os.path.basename(tmp_path)}",
    )
    os.makedirs(artifact_uri, exist_ok=True)
    try:
        materializer = HarborShardResultMaterializer(uri=artifact_uri)
        materializer.save(_shard_result(job_dir=str(job_dir)))
        assert os.path.exists(os.path.join(artifact_uri, "result.json"))
        assert os.path.exists(os.path.join(artifact_uri, "job_dir.tar.gz"))

        result = materializer.load(HarborShardResult)
        assert result.archive_uri is not None
        assert result.job_dir is None

        restored = result.download_jobs_dir(tmp_path / "restored")
        assert (
            restored / "trial-1" / "result.json"
        ).read_text() == '{"ok": true}'
    finally:
        shutil.rmtree(artifact_uri, ignore_errors=True)


def test_materializer_warns_on_dangling_job_dir(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A job_dir that no longer exists is skipped loudly, not silently."""
    from zenml.client import Client

    artifact_uri = os.path.join(
        Client().active_stack.artifact_store.path,
        f"harbor-dangling-test-{os.path.basename(tmp_path)}",
    )
    os.makedirs(artifact_uri, exist_ok=True)
    try:
        materializer = HarborShardResultMaterializer(uri=artifact_uri)
        with caplog.at_level("WARNING"):
            materializer.save(_shard_result(job_dir=str(tmp_path / "gone")))
        assert "does not exist" in caplog.text
        assert not os.path.exists(os.path.join(artifact_uri, "job_dir.tar.gz"))
        assert os.path.exists(os.path.join(artifact_uri, "result.json"))
    finally:
        shutil.rmtree(artifact_uri, ignore_errors=True)


def test_materializer_prunes_temp_job_dir_after_archive(
    tmp_path: Path,
) -> None:
    """A successful archive removes a zenml-harbor- temp source tree."""
    from zenml.client import Client

    temp_root = Path(tempfile.mkdtemp(prefix="zenml-harbor-"))
    job_dir = temp_root / "shard-abc123def456"
    (job_dir / "trial-1").mkdir(parents=True)
    (job_dir / "trial-1" / "result.json").write_text('{"ok": true}')

    artifact_uri = os.path.join(
        Client().active_stack.artifact_store.path,
        f"harbor-prune-test-{os.path.basename(tmp_path)}",
    )
    os.makedirs(artifact_uri, exist_ok=True)
    try:
        materializer = HarborShardResultMaterializer(uri=artifact_uri)
        materializer.save(_shard_result(job_dir=str(job_dir)))
        assert os.path.exists(os.path.join(artifact_uri, "job_dir.tar.gz"))
        # The whole zenml-harbor- temp dir is pruned, not just its child.
        assert not temp_root.exists()
    finally:
        shutil.rmtree(artifact_uri, ignore_errors=True)
        shutil.rmtree(temp_root, ignore_errors=True)


def test_materializer_leaves_non_temp_job_dir(tmp_path: Path) -> None:
    """A job dir outside the zenml-harbor- temp convention is untouched.

    The prune step must never delete an arbitrary user path — only the
    integration's own temp trees.
    """
    from zenml.client import Client

    job_dir = tmp_path / "user-owned" / "shard-abc123def456"
    (job_dir / "trial-1").mkdir(parents=True)
    (job_dir / "trial-1" / "result.json").write_text('{"ok": true}')

    artifact_uri = os.path.join(
        Client().active_stack.artifact_store.path,
        f"harbor-noprune-test-{os.path.basename(tmp_path)}",
    )
    os.makedirs(artifact_uri, exist_ok=True)
    try:
        materializer = HarborShardResultMaterializer(uri=artifact_uri)
        materializer.save(_shard_result(job_dir=str(job_dir)))
        assert os.path.exists(os.path.join(artifact_uri, "job_dir.tar.gz"))
        # The user-owned tree is archived but left in place.
        assert job_dir.exists()
    finally:
        shutil.rmtree(artifact_uri, ignore_errors=True)


def test_materializer_metadata() -> None:
    """The extracted metadata carries the queryable campaign facts."""
    materializer = HarborShardResultMaterializer(uri="unused-uri")
    metadata = materializer.extract_metadata(_shard_result())
    assert metadata["shard_id"] == "abc123def456"
    assert metadata["task"] == "hello"
    assert metadata["agent"] == "oracle"
    assert metadata["model"] == "claude-fable-5"
    assert metadata["n_trials"] == 1
    assert metadata["n_succeeded"] == 1
    assert metadata["n_errored"] == 0
    assert metadata["mean_reward"] == {"reward": 1.0}
    assert metadata["cost_usd"] == 0.01


def test_materializer_content_hash_ignores_transient_fields() -> None:
    """The content hash is stable across differing local job dirs."""
    materializer = HarborShardResultMaterializer(uri="unused-uri")
    a = _shard_result(job_dir="local/dir-a")
    b = _shard_result(job_dir="local/dir-b")
    b.archive_uri = "s3://bucket/somewhere.tar.gz"
    assert materializer.compute_content_hash(
        a
    ) == materializer.compute_content_hash(b)
