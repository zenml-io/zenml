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
"""Pydantic models for Harbor eval campaigns run through ZenML.

These models are the contract between the campaign steps, the shard-result
materializer, and downstream consumers. They deliberately do not import
``harbor`` so that they stay importable (and the materializer registrable)
without Harbor installed; conversion from Harbor's own result objects
happens in ``from_harbor`` factories that receive them untyped.
"""

import os
import re
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from zenml.io import fileio
from zenml.utils.io_utils import is_path_within_directory

# Prefix marking a task ref that points at a git-hosted Harbor task,
# pinned as ``git+URL@COMMIT:SUBPATH`` (the format `harbor` datasets
# resolve to).
GIT_TASK_PREFIX = "git+"

# Prefix of the per-shard temp directory a campaign step creates for
# Harbor's job tree. Shared with the materializer, which prunes such a
# directory after it has archived the tree into the artifact store — the
# prefix bounds that deletion to the integration's own temp dirs.
HARBOR_JOBS_DIR_PREFIX = "zenml-harbor-"


class TaskRef(BaseModel):
    """Reference to one Harbor task, local or git-pinned.

    Mirrors the fields of Harbor's job-level ``TaskConfig`` that identify
    a task, so a ref survives the round trip client -> shard parameters ->
    Harbor job without losing the commit pin a dataset resolved to.
    """

    path: Optional[str] = None
    git_url: Optional[str] = None
    git_commit_id: Optional[str] = None
    name: Optional[str] = None
    ref: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def parse(cls, task_spec: str) -> "TaskRef":
        """Parse a user-supplied task spec string.

        Args:
            task_spec: Either a local task directory path or a
                ``git+URL@COMMIT:SUBPATH`` ref (the pinned format produced
                by dataset resolution).

        Returns:
            The parsed task reference.

        Raises:
            ValueError: If a ``git+`` spec is malformed — e.g. lacks the
                ``@COMMIT`` pin (in which case the userinfo ``@`` of an
                ssh URL would otherwise be misparsed as the pin
                separator), or pins a branch/tag instead of a commit
                SHA. Mutable pins would move underneath shard caching
                and trial-identity baselines.
        """
        if task_spec.startswith(GIT_TASK_PREFIX):
            url, sep, pinned = task_spec[len(GIT_TASK_PREFIX) :].rpartition(
                "@"
            )
            pin, _, subpath = pinned.partition(":")
            # Dataset-resolved refs always carry scheme URLs; requiring
            # '://' catches ssh 'git@host:...' specs whose userinfo '@'
            # would otherwise be misparsed as the pin separator.
            if not sep or "://" not in url:
                raise ValueError(
                    f"Invalid git task ref {task_spec!r}: expected "
                    "'git+URL@COMMIT:SUBPATH'."
                )
            if not re.fullmatch(r"[0-9a-fA-F]{7,40}", pin):
                raise ValueError(
                    f"Invalid git task ref {task_spec!r}: the pin after "
                    f"'@' must be a commit SHA, got {pin!r}. Branch and "
                    "tag pins move underneath shard caching and "
                    "trial-identity baselines; pin the exact commit "
                    "instead."
                )
            # For git-backed tasks, Harbor's TaskConfig carries the
            # task's subpath within the repository in `path`.
            return cls(
                git_url=url or None,
                git_commit_id=pin or None,
                path=subpath or None,
            )
        return cls(path=task_spec)

    def to_string(self) -> str:
        """Canonical string form of this task reference.

        This string is the identity basis for ``trial_identity``, so
        every task shape must render distinctly: ``git+URL@PIN:SUBPATH``
        for git-pinned tasks, the plain path for local tasks, and
        ``NAME@REF`` for registry package tasks (which carry neither a
        path nor a git URL — an empty fallback would collapse all of
        them into one identity).

        Returns:
            The canonical task coordinates, or an empty string for a
            reference with no identifying fields at all.
        """
        if self.git_url:
            return (
                f"{GIT_TASK_PREFIX}{self.git_url}"
                f"@{self.git_commit_id or self.ref or ''}"
                f":{self.path or ''}"
            )
        if self.path:
            return self.path
        if self.name:
            return f"{self.name}@{self.ref or ''}"
        return ""

    @property
    def display_name(self) -> str:
        """Short task label for reports and metadata.

        Returns:
            The last component of the task's name or path.
        """
        if self.path:
            return Path(self.path).name
        return self.name or self.to_string()


class HarborShardSpec(BaseModel):
    """One mapped unit of a campaign: k trials of one (task, agent) cell.

    A shard maps 1:1 onto a Harbor job with a single task, a single agent
    and ``n_attempts == len(trial_indices)``. Keeping every shard inside
    one campaign cell means a shard failure (and its rerun after a step
    retry or cache miss) invalidates the narrowest possible slice of the
    campaign.
    """

    shard_id: str
    task: TaskRef
    agent_name: str
    model_name: Optional[str] = None
    agent_kwargs: Dict[str, Any] = Field(default_factory=dict)
    agent_env: Dict[str, str] = Field(default_factory=dict)
    trial_indices: List[int]
    trial_identities: List[str]


class HarborTrialResult(BaseModel):
    """Flat summary of one Harbor trial, extracted from its result.

    ``task_checksum`` is Harbor's content hash of the task definition —
    the content-addressed complement to the coordinate-based
    ``trial_identity`` (it joins trials of the same task content even
    when specified via different local paths). ``sandbox_flavor`` and
    ``sandbox_docker_image`` are stamped by the shard runner from what
    the environment bridge recorded at session start: the bridge is the
    only party that knows which image actually backed a trial when the
    task pins a ``docker_image`` override.
    """

    trial_identity: str
    trial_name: str
    task_name: str
    source: Optional[str] = None
    task_checksum: Optional[str] = None
    sandbox_flavor: Optional[str] = None
    sandbox_docker_image: Optional[str] = None
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    rewards: Optional[Dict[str, float]] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    n_input_tokens: Optional[int] = None
    n_cache_tokens: Optional[int] = None
    n_output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @classmethod
    def from_harbor(
        cls, trial_result: Any, trial_identity: str
    ) -> "HarborTrialResult":
        """Convert a Harbor ``TrialResult`` into the flat summary model.

        Args:
            trial_result: A ``harbor.models.trial.result.TrialResult``
                (untyped here so this module stays importable without
                Harbor).
            trial_identity: The stable identity hash assigned to this
                trial by the campaign matrix.

        Returns:
            The flat trial summary.

        Raises:
            NotImplementedError: If the trial ran a multi-step task,
                which the ZenML integration does not support yet.
        """
        if trial_result.step_results:
            raise NotImplementedError(
                f"Trial '{trial_result.trial_name}' produced step results, "
                "meaning it ran a Harbor multi-step task. The ZenML Harbor "
                "integration does not support multi-step tasks yet."
            )
        agent_info = trial_result.agent_info
        model_info = agent_info.model_info if agent_info else None
        verifier_result = trial_result.verifier_result
        exception_info = trial_result.exception_info
        n_input, n_cache, n_output, cost = (
            trial_result.compute_token_cost_totals()
        )
        return cls(
            trial_identity=trial_identity,
            trial_name=trial_result.trial_name,
            task_name=trial_result.task_name,
            source=trial_result.source,
            task_checksum=trial_result.task_checksum,
            agent_name=agent_info.name if agent_info else None,
            model_name=model_info.name if model_info else None,
            rewards={
                key: float(value)
                for key, value in verifier_result.rewards.items()
            }
            if verifier_result and verifier_result.rewards
            else None,
            exception_type=exception_info.exception_type
            if exception_info
            else None,
            exception_message=exception_info.exception_message
            if exception_info
            else None,
            n_input_tokens=n_input,
            n_cache_tokens=n_cache,
            n_output_tokens=n_output,
            cost_usd=cost,
            started_at=trial_result.started_at,
            finished_at=trial_result.finished_at,
        )


class HarborShardResult(BaseModel):
    """Result of one campaign shard (one Harbor job).

    The heavyweight part of a shard result — Harbor's ``jobs/`` tree with
    agent/verifier logs and trajectories — is not held in memory. During
    the step, ``job_dir`` points at the still-alive local job directory
    and the materializer archives it next to this model; after loading,
    ``archive_uri`` points at that archive in the artifact store and
    ``download_jobs_dir`` restores it on demand.
    """

    spec: HarborShardSpec
    job_id: str
    job_name: str
    n_total_trials: int
    n_completed: int
    n_errored: int
    n_cancelled: int
    n_retries: int
    trials: List[HarborTrialResult]

    job_dir: Optional[str] = Field(default=None, exclude=True)
    archive_uri: Optional[str] = Field(default=None, exclude=True)

    @property
    def n_succeeded(self) -> int:
        """Trials that finished without erroring.

        Harbor's ``n_completed`` counts every finished trial, errored
        ones included — reporting it as-is reads as a contradiction
        ("Completed=1, Errored=1" for a single crashed trial).

        Returns:
            The number of trials that finished without an error.
        """
        return max(self.n_completed - self.n_errored, 0)

    @property
    def error_rate(self) -> float:
        """Fraction of the shard's trials that errored.

        Returns:
            ``n_errored / n_total_trials``, or 0.0 for an empty shard.
        """
        if not self.n_total_trials:
            return 0.0
        return self.n_errored / self.n_total_trials

    @property
    def mean_reward(self) -> Optional[Dict[str, float]]:
        """Per-key mean reward across the shard's scored trials.

        Returns:
            One mean per reward key, or None if no trial was scored.
        """
        sums: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for trial in self.trials:
            for key, value in (trial.rewards or {}).items():
                sums[key] = sums.get(key, 0.0) + value
                counts[key] = counts.get(key, 0) + 1
        if not counts:
            return None
        return {key: sums[key] / counts[key] for key in sums}

    @property
    def total_cost_usd(self) -> Optional[float]:
        """Total LLM cost across the shard's trials.

        Returns:
            The summed cost, or None if no trial reported one.
        """
        costs = [t.cost_usd for t in self.trials if t.cost_usd is not None]
        return sum(costs) if costs else None

    def download_jobs_dir(self, target_dir: Union[str, Path]) -> Path:
        """Restore the archived Harbor job directory from the artifact store.

        Args:
            target_dir: Local directory to extract the job tree into.

        Returns:
            The path to the extracted job directory.

        Raises:
            RuntimeError: If this result carries no archive reference,
                i.e. it wasn't loaded from the artifact store or the
                shard's job directory was never archived.
        """
        if not self.archive_uri:
            raise RuntimeError(
                "This shard result has no job archive to download. Load "
                "the result from the artifact store (e.g. via "
                "`artifact_version.load()`) so the archive URI is "
                "populated."
            )
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        local_archive = target / os.path.basename(self.archive_uri)
        fileio.copy(self.archive_uri, str(local_archive), overwrite=True)
        with tarfile.open(local_archive, "r:gz") as tar:
            safe_members = [
                member
                for member in tar.getmembers()
                if _is_safe_tar_member(member, str(target))
            ]
            tar.extractall(path=target, members=safe_members)  # nosec B202 - members are filtered through _is_safe_tar_member
        local_archive.unlink()
        return target


def _is_safe_tar_member(member: tarfile.TarInfo, directory: str) -> bool:
    """Check if a tar member is safe to extract.

    Validates that the member name and any link targets stay within the
    target directory to prevent path traversal attacks.

    Args:
        member: The tar member to validate.
        directory: The target extraction directory.

    Returns:
        True if the member is safe to extract, False otherwise.
    """
    if not is_path_within_directory(member.name, directory):
        return False
    if member.issym() or member.islnk():
        return is_path_within_directory(member.linkname, directory)
    return True
