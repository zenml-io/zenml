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
"""Harbor->RL trajectory exporter (spike B3).

Converts the per-trial results of one or more Harbor eval campaign runs
into a single accumulating "RL episode candidates" dataset artifact.
Each record is keyed by the campaign's sha256 ``trial_identity`` (the
cross-run join key minted by ``build_harbor_matrix``) plus the shard
artifact version that produced it, so exporting the same campaign twice
is idempotent and records from run N and run N+1 stay joinable by
identity.

The exporter consumes the campaign's shard artifacts as real step
inputs — one ``normalize_shard`` step call per shard artifact — so
the dashboard shows a lineage path from every eval trial to the dataset
version it fed. (A single step taking ``List[ArtifactVersionResponse]``
would be simpler, but ZenML only resolves artifact-version inputs at
the top level of a step signature, not nested in lists — see
B3_EXPORTER.md.) When a previous dataset version exists it is consumed
as an input too, chaining dataset versions into an append-only
regression suite.

Invocation::

    python export_episodes.py <run_name_or_id> [<run_name_or_id> ...]
"""

import sys
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import log_metadata, pipeline, step
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.harbor.models import (
    HarborShardResult,
    HarborTrialResult,
)
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse

logger = get_logger(__name__)

DATASET_ARTIFACT_NAME = "rl_episode_candidates"


class TrajectoryRef(BaseModel):
    """Pointer to one trial's raw trajectory inside a shard job archive.

    The trajectory itself (agent logs, verifier logs, filesystem
    artifacts) stays in the shard artifact's ``job_dir.tar.gz``; this
    reference is enough to restore it on demand::

        shard = Client().get_artifact_version(ref.shard_artifact_version_id)
        job_dir = shard.load().download_jobs_dir(target)
        trial_dir = job_dir / ref.trial_dir
    """

    shard_artifact_version_id: UUID
    trial_dir: str


class EpisodeCandidate(BaseModel):
    """One Harbor trial, normalized as an RL training-data candidate."""

    trial_identity: str
    trial_name: str
    task_ref: str
    task_name: str
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    rewards: Optional[Dict[str, float]] = None
    reward: Optional[float] = None
    errored: bool = False
    exception_type: Optional[str] = None
    sandbox_flavor: Optional[str] = None
    sandbox_image: Optional[str] = None
    source_run_id: UUID
    source_run_name: str
    trajectory: TrajectoryRef
    n_input_tokens: Optional[int] = None
    n_output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def key(self) -> Any:
        """Uniqueness key within the accumulated dataset.

        The identity says *what* was attempted (pinned task + full agent
        config + trial index); the shard artifact version pins *which
        physical execution* produced the result. Keying on the artifact
        version instead of the source run means a cache-hit campaign
        rerun (same artifact versions, new run) adds nothing, while a
        genuine re-attempt (new shard execution, new artifact version)
        of the same identity lands as a new record.

        Returns:
            The (trial_identity, shard_artifact_version_id) tuple.
        """
        return (
            self.trial_identity,
            self.trajectory.shard_artifact_version_id,
        )


class ShardSource(BaseModel):
    """Provenance of one shard artifact, resolved by the pipeline.

    A loaded ``HarborShardResult`` no longer knows which artifact
    version or pipeline run it came from, so the pipeline resolves that
    (plus the sandbox component of the producing run's stack) and passes
    it alongside the artifact itself.
    """

    artifact_version_id: UUID
    run_id: UUID
    run_name: str
    sandbox_flavor: Optional[str] = None
    sandbox_image: Optional[str] = None


class EpisodeCandidateDataset(BaseModel):
    """Accumulating dataset of RL episode candidates."""

    records: List[EpisodeCandidate] = Field(default_factory=list)

    @property
    def identities(self) -> Any:
        """Distinct trial identities across all records.

        Returns:
            The set of trial_identity hashes in the dataset.
        """
        return {r.trial_identity for r in self.records}


def _to_record(
    trial: HarborTrialResult,
    shard: HarborShardResult,
    source: ShardSource,
) -> EpisodeCandidate:
    """Normalize one Harbor trial into an episode-candidate record.

    Args:
        trial: The flat trial summary from the shard result.
        shard: The shard result the trial belongs to.
        source: Provenance of the shard artifact.

    Returns:
        The normalized record.
    """
    rewards = trial.rewards or None
    # Harbor rewards are a dict; 'reward' is the conventional primary
    # key (it is what verifiers write to reward.txt). Fall back to a
    # single-entry dict's only value so downstream filters stay simple.
    primary: Optional[float] = None
    if rewards:
        if "reward" in rewards:
            primary = rewards["reward"]
        elif len(rewards) == 1:
            primary = next(iter(rewards.values()))
    return EpisodeCandidate(
        trial_identity=trial.trial_identity,
        trial_name=trial.trial_name,
        task_ref=shard.spec.task.to_string(),
        task_name=trial.task_name,
        agent_name=trial.agent_name or shard.spec.agent_name,
        model_name=trial.model_name or shard.spec.model_name,
        rewards=rewards,
        reward=primary,
        errored=trial.exception_type is not None,
        exception_type=trial.exception_type,
        sandbox_flavor=source.sandbox_flavor,
        sandbox_image=source.sandbox_image,
        source_run_id=source.run_id,
        source_run_name=source.run_name,
        trajectory=TrajectoryRef(
            shard_artifact_version_id=source.artifact_version_id,
            trial_dir=trial.trial_name,
        ),
        n_input_tokens=trial.n_input_tokens,
        n_output_tokens=trial.n_output_tokens,
        cost_usd=trial.cost_usd,
        started_at=trial.started_at,
        finished_at=trial.finished_at,
    )


@step
def normalize_shard(
    shard: HarborShardResult,
    source: Dict[str, Any],
) -> Annotated[EpisodeCandidateDataset, "episode_candidate_batch"]:
    """Normalize one shard artifact's trials into episode candidates.

    Called once per shard artifact of the source campaign run(s): the
    shard artifact is consumed as a real step input, which is what
    records the lineage edge from the eval trial to the exported
    dataset.

    Args:
        shard: One shard artifact of a previous campaign run.
        source: ``ShardSource`` provenance for exactly this artifact.

    Returns:
        The shard's trials as a record batch.
    """
    parsed = ShardSource.model_validate(source)
    return EpisodeCandidateDataset(
        records=[_to_record(t, shard, parsed) for t in shard.trials]
    )


@step
def merge_episode_candidates(
    batches: List[EpisodeCandidateDataset],
    previous: Optional[EpisodeCandidateDataset] = None,
) -> Annotated[EpisodeCandidateDataset, DATASET_ARTIFACT_NAME]:
    """Merge record batches into the accumulating dataset.

    Args:
        batches: Per-shard record batches from ``normalize_shard``.
        previous: The latest existing dataset version, if any; new
            records are appended to it.

    Returns:
        The grown dataset. Records are deduplicated on
        (trial_identity, source_run_id), so re-exporting an
        already-exported run is a no-op.
    """
    dataset = EpisodeCandidateDataset(
        records=list(previous.records) if previous else []
    )
    seen = {r.key for r in dataset.records}
    n_new = 0
    for batch in batches:
        for record in batch.records:
            if record.key in seen:
                continue
            seen.add(record.key)
            dataset.records.append(record)
            n_new += 1

    scored = [r.reward for r in dataset.records if r.reward is not None]
    metadata: Dict[str, Any] = {
        "rl_export.n_records": len(dataset.records),
        "rl_export.n_new_records": n_new,
        "rl_export.n_distinct_identities": len(dataset.identities),
        "rl_export.n_source_runs": len(
            {r.source_run_id for r in dataset.records}
        ),
        "rl_export.n_errored": sum(1 for r in dataset.records if r.errored),
    }
    if scored:
        metadata["rl_export.mean_reward"] = sum(scored) / len(scored)
    log_metadata(metadata=metadata)
    logger.info(
        "Exported %d new episode candidate(s); dataset now holds %d "
        "record(s) across %d distinct trial identit(ies).",
        n_new,
        len(dataset.records),
        len(dataset.identities),
    )
    return dataset


def _resolve_sandbox(run: PipelineRunResponse) -> Dict[str, Optional[str]]:
    """Best-effort sandbox provenance from a run's stack.

    The Harbor job archives do not record which sandbox flavor/image a
    trial executed in (a provenance gap in its own right — see
    B3_EXPORTER.md), so the exporter falls back to the sandbox component
    of the stack the campaign ran on. Task-level ``docker_image`` pins
    (Terminal-Bench) override the component image at runtime and are
    NOT visible here.

    Args:
        run: The producing pipeline run response.

    Returns:
        Dict with 'flavor' and 'image' (either may be None).
    """
    stack = run.stack
    if stack is None:
        return {"flavor": None, "image": None}
    components = stack.components.get(StackComponentType.SANDBOX) or []
    if not components:
        return {"flavor": None, "image": None}
    component = Client().get_stack_component(
        StackComponentType.SANDBOX, str(components[0].id)
    )
    return {
        "flavor": component.flavor_name,
        "image": component.configuration.get("image"),
    }


@pipeline(dynamic=True, enable_cache=False)
def export_rl_episode_candidates(run_names_or_ids: List[str]) -> None:
    """Export the trials of one or more campaign runs into the dataset.

    Args:
        run_names_or_ids: Names or IDs of ``harbor_agent_evals``
            pipeline runs whose shard artifacts should be exported.

    Raises:
        ValueError: If the given runs contain no shard artifacts.
    """
    client = Client()
    shard_artifacts = []
    sources: List[Dict[str, Any]] = []
    for ref in run_names_or_ids:
        run = client.get_pipeline_run(ref)
        sandbox = _resolve_sandbox(run)
        for name, step_run in sorted((run.steps or {}).items()):
            if not name.startswith("map:run_harbor_shard"):
                continue
            output = step_run.outputs.get("harbor_shard_result")
            if not output:
                logger.warning(
                    "Step %s of run %s has no shard result output; skipping.",
                    name,
                    run.name,
                )
                continue
            artifact_version = output[0]
            shard_artifacts.append(artifact_version)
            sources.append(
                ShardSource(
                    artifact_version_id=artifact_version.id,
                    run_id=run.id,
                    run_name=run.name,
                    sandbox_flavor=sandbox["flavor"],
                    sandbox_image=sandbox["image"],
                ).model_dump(mode="json")
            )
    if not shard_artifacts:
        raise ValueError(
            f"No shard artifacts found in run(s) {run_names_or_ids}."
        )

    previous = None
    existing = client.list_artifact_versions(
        artifact=DATASET_ARTIFACT_NAME, sort_by="desc:created", size=1
    )
    if existing.items:
        previous = existing.items[0]
        logger.info(
            "Appending to dataset version %s (%s).",
            previous.version,
            previous.id,
        )

    # Not `.map(...)`: mapping only works over step outputs of the
    # current run, and a `List[ArtifactVersionResponse]` step input is
    # passed through as a raw parameter instead of being resolved. A
    # plain loop over single artifact-version inputs is the shape that
    # both loads the artifacts and records the lineage edges.
    batches = [
        normalize_shard(shard=artifact_version, source=source)
        for artifact_version, source in zip(shard_artifacts, sources)
    ]
    merge_episode_candidates(batches=batches, previous=previous)


if __name__ == "__main__":
    refs = sys.argv[1:]
    if not refs:
        print(
            "Usage: python export_episodes.py <run_name_or_id> "
            "[<run_name_or_id> ...]"
        )
        sys.exit(1)
    export_rl_episode_candidates(run_names_or_ids=refs)

    # Receipt: show the dataset version this export produced.
    client = Client()
    version = client.list_artifact_versions(
        artifact=DATASET_ARTIFACT_NAME, sort_by="desc:created", size=1
    ).items[0]
    dataset = version.load()
    print(
        f"\nDataset '{DATASET_ARTIFACT_NAME}' version {version.version}: "
        f"{len(dataset.records)} record(s), "
        f"{len(dataset.identities)} distinct trial identit(ies)."
    )
    for record in dataset.records[:10]:
        print(
            f"  {record.trial_identity[:12]}  reward={record.reward}  "
            f"agent={record.agent_name}  task={record.task_name}  "
            f"run={record.source_run_name[-26:]}"
        )
