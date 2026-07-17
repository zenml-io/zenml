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
"""Materializer for Harbor campaign shard results."""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Tuple, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.integrations.harbor.models import (
    HARBOR_JOBS_DIR_PREFIX,
    HarborShardResult,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)

RESULT_FILENAME = "result.json"
ARCHIVE_FILENAME = "job_dir.tar.gz"
VISUALIZATION_FILENAME = "shard_report.md"


def _prunable_temp_job_root(job_dir: str) -> Optional[str]:
    """The ``zenml-harbor-`` temp directory safe to prune, or None.

    Bounds job-tree deletion to the integration's own temp dirs: the
    returned path must be a direct child of the system temp directory
    whose name carries the ``zenml-harbor-`` prefix (the campaign step's
    ``mkdtemp`` convention). Any job dir outside that convention — a
    user-supplied path, a non-temp location, a nested match — yields
    None, so deletion never touches an arbitrary path.

    Args:
        job_dir: The local Harbor job directory recorded on the result.

    Returns:
        The prunable temp directory, or None if deletion would be unsafe.
    """
    resolved = Path(job_dir).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.parent == temp_root:
            if candidate.name.startswith(HARBOR_JOBS_DIR_PREFIX):
                return str(candidate)
            return None
    return None


class HarborShardResultMaterializer(BaseMaterializer):
    """Materializer for :class:`HarborShardResult`.

    Persists the flat shard summary as JSON and Harbor's job directory
    (agent/verifier logs, trajectories) as a gzipped tar archive next to
    it. Loading restores only the summary; the archive is fetched on
    demand via ``HarborShardResult.download_jobs_dir``.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (HarborShardResult,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save(self, data: HarborShardResult) -> None:
        """Save the shard summary and archive the Harbor job directory.

        Args:
            data: The shard result to save. If its ``job_dir`` points at
                an existing local directory, that directory is archived
                into the artifact store alongside the summary.
        """
        with self.artifact_store.open(
            os.path.join(self.uri, RESULT_FILENAME), "w"
        ) as f:
            f.write(data.model_dump_json(indent=2))

        if data.job_dir and not os.path.isdir(data.job_dir):
            logger.warning(
                "Harbor job directory %s does not exist; saving shard "
                "result without a job archive. Logs and trajectories "
                "will not be recoverable via download_jobs_dir().",
                data.job_dir,
            )
        if data.job_dir and os.path.isdir(data.job_dir):
            with self.get_temporary_directory(
                delete_at_exit=True
            ) as directory:
                archive_base = os.path.join(directory, "job_dir")
                shutil.make_archive(
                    base_name=archive_base,
                    format="gztar",
                    root_dir=data.job_dir,
                )
                fileio.copy(
                    f"{archive_base}.tar.gz",
                    os.path.join(self.uri, ARCHIVE_FILENAME),
                )
            # The artifact-store archive is now the durable copy, so the
            # transient local job tree can go. This runs here, not in the
            # step, because output materialization happens after the step
            # function returns — a `finally` in the step body would delete
            # the tree before this save() ever archived it.
            self._prune_temp_job_dir(data.job_dir)

    def _prune_temp_job_dir(self, job_dir: str) -> None:
        """Delete the local Harbor job tree once it is safely archived.

        Deletion is restricted to the integration's own
        ``zenml-harbor-`` temp directories (see
        :func:`_prunable_temp_job_root`), so a user-supplied ``job_dir``
        is never removed.

        Args:
            job_dir: The local Harbor job directory that was archived.
        """
        prunable = _prunable_temp_job_root(job_dir)
        if prunable is None:
            return
        try:
            shutil.rmtree(prunable)
        except OSError:
            logger.warning(
                "Failed to prune archived Harbor job dir %s; it may "
                "persist under the system temp dir until the OS reaps it.",
                prunable,
                exc_info=True,
            )

    def load(self, data_type: Type[Any]) -> HarborShardResult:
        """Load the shard summary without unpacking the job archive.

        Args:
            data_type: Unused.

        Returns:
            The shard result, with ``archive_uri`` set if a job archive
            exists in the artifact store.
        """
        with self.artifact_store.open(
            os.path.join(self.uri, RESULT_FILENAME), "r"
        ) as f:
            result = HarborShardResult.model_validate_json(f.read())
        archive_uri = os.path.join(self.uri, ARCHIVE_FILENAME)
        if self.artifact_store.exists(archive_uri):
            result.archive_uri = archive_uri.replace("\\", "/")
        return result

    def extract_metadata(
        self, data: HarborShardResult
    ) -> Dict[str, MetadataType]:
        """Extract queryable metadata from the shard result.

        Args:
            data: The shard result.

        Returns:
            Flat metadata describing the shard's campaign cell and
            outcome.
        """
        metadata: Dict[str, MetadataType] = {
            "shard_id": data.spec.shard_id,
            "task": data.spec.task.display_name,
            "agent": data.spec.agent_name,
            "n_trials": len(data.spec.trial_indices),
            "n_succeeded": data.n_succeeded,
            "n_errored": data.n_errored,
            "error_rate": data.error_rate,
            "n_retries": data.n_retries,
        }
        if data.spec.model_name:
            metadata["model"] = data.spec.model_name
        mean_reward = data.mean_reward
        if mean_reward is not None:
            metadata["mean_reward"] = mean_reward
        cost = data.total_cost_usd
        if cost is not None:
            metadata["cost_usd"] = cost
        return metadata

    def save_visualizations(
        self, data: HarborShardResult
    ) -> Dict[str, VisualizationType]:
        """Render the shard as a small Markdown report.

        Args:
            data: The shard result.

        Returns:
            A single Markdown visualization keyed by its URI.
        """
        lines = [
            f"# Harbor shard `{data.spec.shard_id[:12]}`",
            "",
            f"Task `{data.spec.task.display_name}` · agent "
            f"`{data.spec.agent_name}`"
            + (
                f" · model `{data.spec.model_name}`"
                if data.spec.model_name
                else ""
            ),
            "",
            f"{data.n_succeeded} succeeded, {data.n_errored} errored, "
            f"{data.n_retries} retried (Harbor job `{data.job_name}`).",
            "",
            "| Trial | Rewards | Error | Cost (USD) |",
            "|---|---|---|---|",
        ]
        for trial in data.trials:
            rewards = (
                ", ".join(
                    f"{key}={value:g}" for key, value in trial.rewards.items()
                )
                if trial.rewards
                else "n/a"
            )
            cost = (
                f"{trial.cost_usd:.4f}"
                if trial.cost_usd is not None
                else "n/a"
            )
            lines.append(
                f"| {trial.trial_name} | {rewards} | "
                f"{trial.exception_type or ''} | {cost} |"
            )
        visualization_uri = os.path.join(self.uri, VISUALIZATION_FILENAME)
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write("\n".join(lines))
        return {
            visualization_uri.replace("\\", "/"): VisualizationType.MARKDOWN
        }

    def compute_content_hash(self, data: HarborShardResult) -> Optional[str]:
        """Compute a stable content hash of the shard summary.

        The transient ``job_dir``/``archive_uri`` fields are excluded
        from serialization, so the hash is stable across save/load.

        Args:
            data: The shard result.

        Returns:
            An md5 hex digest of the serialized summary.
        """
        hash_ = hashlib.md5(usedforsecurity=False)
        hash_.update(type(data).__name__.encode())
        hash_.update(data.model_dump_json().encode())
        return hash_.hexdigest()
