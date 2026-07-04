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
"""Programmatic Harbor job execution for campaign shards.

This module imports ``harbor`` at the top level and must therefore only
be imported from code that runs with Harbor installed (the campaign
steps, user pipelines) — never from the integration's ``__init__`` or
``activate()`` paths.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from harbor.job import Job
from harbor.models.job.config import DatasetConfig, JobConfig, RetryConfig
from harbor.models.job.result import JobResult
from harbor.models.task.task import Task
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    VerifierConfig,
)

from zenml.integrations.harbor import ZENML_HARBOR_ENV_IMPORT_PATH
from zenml.integrations.harbor.models import (
    HarborShardResult,
    HarborShardSpec,
    HarborTrialResult,
    TaskRef,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


def resolve_dataset(dataset: Dict[str, Any]) -> List[TaskRef]:
    """Resolve a Harbor dataset into pinned task references.

    Uses Harbor's own resolver so the task set and commit pins match
    ``harbor run`` exactly. Registry datasets resolve to git-pinned refs
    that each shard fetches at trial start — nothing is downloaded here.

    Args:
        dataset: Keyword arguments for Harbor's ``DatasetConfig``, e.g.
            ``{"name": "terminal-bench", "version": "2.0"}`` or
            ``{"path": "./my-dataset"}``.

    Returns:
        One task reference per task in the dataset.

    Raises:
        ValueError: If the dataset resolves to no tasks.
    """
    config = DatasetConfig(**dataset)
    # TODO: switch to a public Harbor resolver API when one exists;
    # disable_verification skips local checksum verification only.
    task_configs = asyncio.run(
        config.get_task_configs(disable_verification=True)
    )
    refs = [
        TaskRef(
            path=str(tc.path) if tc.path else None,
            git_url=tc.git_url,
            git_commit_id=tc.git_commit_id,
            name=tc.name,
            ref=tc.ref,
            source=tc.source,
        )
        for tc in task_configs
    ]
    if not refs:
        raise ValueError(f"Dataset {dataset!r} resolved to no tasks.")
    return refs


def build_job_config(
    spec: HarborShardSpec,
    jobs_dir: Path,
    n_concurrent_trials: int = 4,
    timeout_multiplier: float = 1.0,
    harbor_retry_max: int = 0,
) -> JobConfig:
    """Build the single-cell Harbor job config for one campaign shard.

    Args:
        spec: The shard to run.
        jobs_dir: Directory Harbor writes the job tree into.
        n_concurrent_trials: Upper bound on trials Harbor runs
            concurrently inside this shard (capped at the shard size).
        timeout_multiplier: Multiplier applied to all task timeouts.
        harbor_retry_max: Max Harbor-internal retries per errored trial.

    Returns:
        The Harbor job configuration.

    Raises:
        FileNotFoundError: If the shard references a local task
            directory that does not exist.
        NotImplementedError: If the shard references a local multi-step
            task, which the ZenML integration does not support yet.
    """
    task = spec.task
    if task.path and not task.git_url:
        task_dir = Path(task.path)
        if not task_dir.exists():
            raise FileNotFoundError(f"Harbor task path not found: {task_dir}")
        # Git-backed tasks can only be inspected after Harbor fetches
        # them; those are caught per-trial via TrialResult.step_results.
        if Task(task_dir).has_steps:
            raise NotImplementedError(
                f"Harbor task '{task_dir}' defines steps. The ZenML "
                "Harbor integration does not support multi-step tasks "
                "yet."
            )
    return JobConfig(
        job_name=f"shard-{spec.shard_id[:12]}",
        jobs_dir=jobs_dir,
        n_attempts=len(spec.trial_indices),
        n_concurrent_trials=min(n_concurrent_trials, len(spec.trial_indices)),
        timeout_multiplier=timeout_multiplier,
        quiet=True,
        retry=RetryConfig(max_retries=harbor_retry_max),
        tasks=[
            TaskConfig(
                path=Path(task.path) if task.path else None,
                git_url=task.git_url,
                git_commit_id=task.git_commit_id,
                name=task.name,
                ref=task.ref,
                source=task.source,
            )
        ],
        agents=[
            AgentConfig(
                name=spec.agent_name,
                model_name=spec.model_name,
                kwargs=spec.agent_kwargs,
                env=spec.agent_env,
            )
        ],
        environment=EnvironmentConfig(
            import_path=ZENML_HARBOR_ENV_IMPORT_PATH
        ),
        verifier=VerifierConfig(),
    )


def run_shard_job(
    spec: HarborShardSpec,
    jobs_dir: Path,
    n_concurrent_trials: int = 4,
    timeout_multiplier: float = 1.0,
    harbor_retry_max: int = 0,
) -> HarborShardResult:
    """Run one campaign shard as a Harbor job and collect its results.

    Args:
        spec: The shard to run.
        jobs_dir: Directory Harbor writes the job tree into. Must
            outlive the returned result until it is materialized — the
            result's ``job_dir`` points into it.
        n_concurrent_trials: Upper bound on trials Harbor runs
            concurrently inside this shard.
        timeout_multiplier: Multiplier applied to all task timeouts.
        harbor_retry_max: Max Harbor-internal retries per errored trial.

    Returns:
        The shard result, with ``job_dir`` pointing at the local Harbor
        job directory.
    """
    config = build_job_config(
        spec=spec,
        jobs_dir=jobs_dir,
        n_concurrent_trials=n_concurrent_trials,
        timeout_multiplier=timeout_multiplier,
        harbor_retry_max=harbor_retry_max,
    )

    async def _run() -> JobResult:
        job = await Job.create(config)
        return await job.run()

    # ``asyncio.run`` is safe because ZenML steps run synchronously
    # today; revisit if step bodies grow an outer event loop.
    job_result = asyncio.run(_run())

    # The on-disk job-level result.json is always written without trial
    # results; the in-memory JobResult from `job.run()` is the only
    # complete per-trial source. Trials are paired with the shard's
    # precomputed identities by encounter order — Harbor trial names
    # carry random suffixes, so order is the stable join.
    trial_results = job_result.trial_results
    if len(trial_results) != len(spec.trial_identities):
        logger.warning(
            "Harbor job returned %d trial result(s) for a shard of %d "
            "trial(s); pairing trial identities by order as far as "
            "possible.",
            len(trial_results),
            len(spec.trial_identities),
        )
    trials = [
        HarborTrialResult.from_harbor(result, identity)
        for identity, result in zip(spec.trial_identities, trial_results)
    ]
    stats = job_result.stats
    return HarborShardResult(
        spec=spec,
        job_id=str(job_result.id),
        job_name=config.job_name,
        n_total_trials=job_result.n_total_trials,
        n_completed=stats.n_completed_trials,
        n_errored=stats.n_errored_trials,
        n_cancelled=stats.n_cancelled_trials,
        n_retries=stats.n_retries,
        trials=trials,
        job_dir=str(jobs_dir / config.job_name),
    )
