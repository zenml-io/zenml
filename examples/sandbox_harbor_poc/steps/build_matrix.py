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
"""Step: build the evaluation matrix from a YAML config file.

A campaign sources its tasks one of two ways:

* **Local dataset** — ``dataset_path`` points at a directory of task folders
  (each with a ``task.toml``), as in the bundled ``datasets/mini_harbor``.
* **Registry dataset** — ``dataset_name`` (+ ``dataset_version``) names a
  Harbor registry benchmark such as ``terminal-bench`` (89 tasks) or
  ``swebench-verified`` (500 tasks). Harbor resolves it to git-pinned tasks,
  which we expand into one spec per task so ZenML still fans out one Sandbox
  per trial.

Both paths produce the same ``HarborRunSpec`` list; only how a task is located
(local path vs. git url + commit) differs downstream in ``run_harbor_job``.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import yaml
from models.harbor_models import HarborRunSpec

from zenml import step

logger = logging.getLogger(__name__)


class _TaskRef:
    """A single resolved task: its name plus where to fetch it from.

    Local tasks carry only ``path``; registry tasks carry the git coordinates
    (``git_url`` + ``git_commit_id``/``ref``) and ``path`` as the sub-path
    inside the repo.
    """

    def __init__(
        self,
        name: str,
        path: str,
        git_url: Optional[str] = None,
        git_commit_id: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> None:
        self.name = name
        self.path = path
        self.git_url = git_url
        self.git_commit_id = git_commit_id
        self.ref = ref


def _resolve_path(path: str) -> Path:
    """Try multiple locations for a config-relative path.

    On local orchestrators the path is relative to cwd. On Kubernetes
    the code is mounted at /app/ or /app/code/.

    Args:
        path: A relative (or absolute) path from the config.

    Returns:
        The first existing candidate.

    Raises:
        FileNotFoundError: If no candidate exists.
    """
    candidates = [
        Path(path),
        Path(__file__).parent.parent / path,
        Path("/app") / path,
        Path("/app/code") / path,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Path not found. Tried: {[str(c) for c in candidates]}"
    )


def _local_task_refs(dataset_path: str) -> List[_TaskRef]:
    """Resolve a local dataset directory into one task ref per task folder.

    Args:
        dataset_path: Dataset directory from the config.

    Returns:
        Sorted task refs, one per ``*/task.toml`` under the dataset.

    Raises:
        FileNotFoundError: If the dataset has no tasks.
    """
    resolved = _resolve_path(dataset_path)
    names = sorted(p.parent.name for p in resolved.glob("*/task.toml"))
    if not names:
        raise FileNotFoundError(
            f"No Harbor tasks (*/task.toml) found under {resolved}"
        )
    # Keep the path relative so run_harbor_job re-resolves it in its own
    # execution environment.
    return [_TaskRef(name=n, path=f"{dataset_path}/{n}") for n in names]


def _registry_task_refs(
    name: str,
    version: Optional[str],
    n_tasks: Optional[int],
    task_names: Optional[List[str]],
) -> List[_TaskRef]:
    """Resolve a Harbor registry dataset into one git-pinned ref per task.

    Uses Harbor's own ``DatasetConfig.get_task_configs`` so the task set,
    versions and commit pins match exactly what ``harbor run`` would use.
    This only reads the registry/git metadata; the task contents are fetched
    later, per trial, inside ``run_harbor_job``.

    Args:
        name: Registry dataset name, e.g. 'terminal-bench'.
        version: Dataset version, e.g. '2.0' (None for the registry default).
        n_tasks: Optional cap on the number of tasks (applied after filtering).
        task_names: Optional glob patterns selecting tasks to include.

    Returns:
        One task ref per resolved task, carrying its git coordinates.

    Raises:
        ValueError: If the dataset resolves to no tasks.
    """
    from harbor.models.job.config import DatasetConfig

    dataset = DatasetConfig(
        name=name,
        version=version,
        n_tasks=n_tasks,
        task_names=task_names or None,
    )
    task_configs = asyncio.run(
        dataset.get_task_configs(disable_verification=True)
    )
    if not task_configs:
        raise ValueError(
            f"Harbor registry dataset '{name}' (version={version}) resolved "
            f"to no tasks (task_names={task_names}, n_tasks={n_tasks})."
        )
    refs: List[_TaskRef] = []
    for tc in task_configs:
        # Registry tasks set name=None; derive a stable name from the repo
        # sub-path's last segment (e.g. 'sample/chess-best-move' -> 'chess...').
        task_name = tc.name or (Path(tc.path).name if tc.path else "task")
        refs.append(
            _TaskRef(
                name=task_name,
                path=str(tc.path) if tc.path else "",
                git_url=tc.git_url,
                git_commit_id=tc.git_commit_id,
                ref=tc.ref,
            )
        )
    return refs


def _resolve_task_refs(campaign: dict) -> List[_TaskRef]:
    """Resolve the campaign's task source (local or registry) into task refs.

    Args:
        campaign: The ``campaign`` block of the YAML config.

    Returns:
        Task refs for the configured dataset.

    Raises:
        ValueError: If neither ``dataset_path`` nor ``dataset_name`` is set.
    """
    dataset_name = campaign.get("dataset_name")
    dataset_path = campaign.get("dataset_path")
    if dataset_name:
        return _registry_task_refs(
            name=dataset_name,
            version=campaign.get("dataset_version"),
            n_tasks=campaign.get("n_tasks"),
            task_names=campaign.get("task_names"),
        )
    if dataset_path:
        return _local_task_refs(dataset_path)
    raise ValueError(
        "Campaign config must set either 'dataset_path' (local dataset) or "
        "'dataset_name' (Harbor registry dataset)."
    )


def _agent_models(agent: str, models: List[str]) -> List[Optional[str]]:
    """Return the model dimension for an agent.

    The oracle agent runs the reference solution and needs no model, so it
    collapses to a single ``None``; every other agent expands across the
    configured models (or a single ``None`` when none are configured).

    Args:
        agent: Harbor agent name.
        models: Configured model list.

    Returns:
        Models to pair with this agent.
    """
    if agent == "oracle" or not models:
        return [None]
    return list(models)


@step
def build_matrix(config_path: str) -> List[HarborRunSpec]:
    """Read a campaign config and expand it to one spec per trial.

    Fans out the cartesian product of ``agents x models x tasks``: every
    ``(agent, model, task)`` cell becomes one HarborRunSpec, which the
    pipeline maps to its own ``run_harbor_job`` step (one Sandbox each).

    Args:
        config_path: Path to the campaign YAML config file.

    Returns:
        List of HarborRunSpec, one per (agent, model, task) trial.
    """
    resolved = _resolve_path(config_path)
    logger.info("Loading campaign config from %s", resolved)

    with open(resolved, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    campaign = raw.get("campaign", raw)
    agents: List[str] = campaign.get("agents", [])
    models: List[str] = campaign.get("models", [])
    env_provider = campaign.get("env_provider")

    task_refs = _resolve_task_refs(campaign)

    specs: List[HarborRunSpec] = []
    for agent in agents:
        for model in _agent_models(agent, models):
            combo = f"{agent}/{model}" if model else agent
            for ref in task_refs:
                specs.append(
                    HarborRunSpec(
                        agent=agent,
                        model=model,
                        task_path=ref.path,
                        task_name=ref.name,
                        task_git_url=ref.git_url,
                        task_git_commit_id=ref.git_commit_id,
                        task_ref=ref.ref,
                        env_provider=env_provider,
                        label=f"{combo}/{ref.name}",
                    )
                )

    logger.info(
        "Built evaluation matrix with %d trial(s): %s",
        len(specs),
        [s.label for s in specs],
    )
    return specs
