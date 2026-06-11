# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Shape A steps: let Harbor own the job orchestration.

Where the shape-B ``run_harbor_job`` runs ONE task per ZenML step (ZenML owns
the fan-out, concurrency and retries), shape A hands Harbor a *multi-task*
``JobConfig`` so Harbor schedules the trials, runs them concurrently
(``n_concurrent_trials``) and aggregates them — one ZenML step per
``(agent, model)`` combo. The Sandbox bridge is identical; only who
orchestrates the trials changes.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Annotated, List

import yaml
from harbor.job import Job
from harbor.models.job.config import DatasetConfig, JobConfig
from harbor.models.trial.config import (
    EnvironmentConfig,
    TaskConfig,
    VerifierConfig,
)
from models.harbor_models import HarborRunSpec

from steps.build_matrix import _agent_models, _resolve_path
from steps.run_harbor_job import (
    _BRIDGE_IMPORT_PATH,
    _build_agent_config,
    _ensure_modal_credentials,
    _find_job_dir,
    _resolve_task_path,
)
from zenml import log_metadata, step

logger = logging.getLogger(__name__)

# Cap concurrent trials inside a single Harbor job so one step doesn't open an
# unbounded number of Sandbox sessions at once.
_MAX_CONCURRENT_TRIALS = 8


@step
def build_combos(config_path: str) -> List[HarborRunSpec]:
    """Expand the campaign config into one spec per (agent, model) combo.

    Unlike ``build_matrix`` (shape B), the task dimension is NOT expanded — the
    whole dataset path rides on each spec and Harbor iterates the tasks inside
    one job.

    Args:
        config_path: Path to the campaign YAML config file.

    Returns:
        One HarborRunSpec per (agent, model); ``task_path`` is the dataset dir.
    """
    resolved = _resolve_path(config_path)
    with open(resolved, encoding="utf-8") as f:
        campaign = (yaml.safe_load(f) or {}).get("campaign", {})
    agents: List[str] = campaign.get("agents", [])
    models: List[str] = campaign.get("models", [])
    dataset_path: str = campaign.get("dataset_path", "")
    dataset_name = campaign.get("dataset_name")
    dataset_version = campaign.get("dataset_version")
    dataset_n_tasks = campaign.get("n_tasks")
    env_provider = campaign.get("env_provider")

    specs: List[HarborRunSpec] = []
    for agent in agents:
        for model in _agent_models(agent, models):
            combo = f"{agent}/{model}" if model else agent
            specs.append(
                HarborRunSpec(
                    agent=agent,
                    model=model,
                    # The whole dataset rides on each spec: a local path, or a
                    # registry dataset Harbor expands inside the single job.
                    task_path="" if dataset_name else dataset_path,
                    task_name=combo,
                    dataset_name=dataset_name,
                    dataset_version=dataset_version,
                    dataset_n_tasks=dataset_n_tasks,
                    env_provider=env_provider,
                    label=combo,
                )
            )
    logger.info(
        "Built %d job-wise combo(s): %s", len(specs), [s.label for s in specs]
    )
    return specs


def _list_tasks(dataset_dir: Path) -> List[TaskConfig]:
    """One TaskConfig per ``*/task.toml`` under the dataset directory."""
    dirs = sorted(p.parent for p in dataset_dir.glob("*/task.toml"))
    if not dirs:
        raise FileNotFoundError(
            f"No Harbor tasks (*/task.toml) found under {dataset_dir}"
        )
    return [TaskConfig(path=str(d)) for d in dirs]


async def _run_job(config: JobConfig, jobs_dir: Path, label: str) -> Path:
    """Execute the multi-task Harbor job via the Sandbox bridge."""
    job = await Job.create(config)
    result = await job.run()
    logger.info(
        "Harbor job for %s finished: %d trial(s)",
        label,
        result.n_total_trials,
    )
    return _find_job_dir(jobs_dir)


@step(enable_cache=False)
def run_harbor_job_jobwise(spec: HarborRunSpec) -> Annotated[Path, "job_dir"]:
    """Run every dataset task for one agent/model as a single Harbor job.

    Harbor owns the trial scheduling/concurrency here; ZenML wraps the job for
    lineage and the Sandbox substrate. The returned job tree contains all
    trials and is archived as one versioned artifact.

    Args:
        spec: The combo spec (``task_path`` is the dataset directory).

    Returns:
        Path to the Harbor job output directory (all trials).
    """
    _ensure_modal_credentials()

    jobs_dir = Path(tempfile.mkdtemp(prefix="harbor_"))
    common = dict(
        jobs_dir=jobs_dir,
        quiet=True,
        agents=[_build_agent_config(spec)],
        environment=EnvironmentConfig(import_path=_BRIDGE_IMPORT_PATH),
        verifier=VerifierConfig(),
    )

    if spec.dataset_name:
        # Registry dataset: hand the whole dataset to Harbor and let it expand
        # and schedule the trials. n_tasks is unknown until Harbor resolves it,
        # so cap concurrency at the configured maximum.
        logger.info(
            "Running Harbor job for %s over registry dataset %s (v%s, "
            "n_tasks=%s, jobs_dir=%s)",
            spec.label,
            spec.dataset_name,
            spec.dataset_version,
            spec.dataset_n_tasks,
            jobs_dir,
        )
        config = JobConfig(
            n_concurrent_trials=_MAX_CONCURRENT_TRIALS,
            datasets=[
                DatasetConfig(
                    name=spec.dataset_name,
                    version=spec.dataset_version,
                    n_tasks=spec.dataset_n_tasks,
                )
            ],
            **common,
        )
        n_tasks = spec.dataset_n_tasks
    else:
        dataset_dir = _resolve_task_path(spec.task_path)
        tasks = _list_tasks(dataset_dir)
        logger.info(
            "Running Harbor job for %s over %d local task(s) (jobs_dir=%s)",
            spec.label,
            len(tasks),
            jobs_dir,
        )
        config = JobConfig(
            n_concurrent_trials=min(len(tasks), _MAX_CONCURRENT_TRIALS),
            tasks=tasks,
            **common,
        )
        n_tasks = len(tasks)

    job_dir = asyncio.run(_run_job(config, jobs_dir, spec.label))
    log_metadata(
        metadata={
            "agent": spec.agent,
            "model": spec.model or "none",
            "combo": spec.label,
            "dataset": spec.dataset_name or "local",
            "n_tasks": n_tasks if n_tasks is not None else -1,
            "job_dir_name": job_dir.name,
        }
    )
    return job_dir
