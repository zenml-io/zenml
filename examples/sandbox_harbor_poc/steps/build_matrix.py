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
"""Step: build the evaluation matrix from a YAML config file."""

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from models.harbor_models import HarborRunSpec

from zenml import step

logger = logging.getLogger(__name__)


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


def _list_task_names(dataset_path: str) -> List[str]:
    """List task directory names under a dataset (each holds a task.toml).

    Args:
        dataset_path: Dataset directory from the config.

    Returns:
        Sorted task directory names.

    Raises:
        FileNotFoundError: If the dataset has no tasks.
    """
    resolved = _resolve_path(dataset_path)
    names = sorted(p.parent.name for p in resolved.glob("*/task.toml"))
    if not names:
        raise FileNotFoundError(
            f"No Harbor tasks (*/task.toml) found under {resolved}"
        )
    return names


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
    dataset_path: str = campaign.get("dataset_path", "")
    env_provider = campaign.get("env_provider")

    task_names = _list_task_names(dataset_path)

    specs: List[HarborRunSpec] = []
    for agent in agents:
        for model in _agent_models(agent, models):
            combo = f"{agent}/{model}" if model else agent
            for task_name in task_names:
                specs.append(
                    HarborRunSpec(
                        agent=agent,
                        model=model,
                        # Keep the path relative so run_harbor_job can
                        # re-resolve it in its own execution environment.
                        task_path=f"{dataset_path}/{task_name}",
                        task_name=task_name,
                        env_provider=env_provider,
                        label=f"{combo}/{task_name}",
                    )
                )

    logger.info(
        "Built evaluation matrix with %d trial(s): %s",
        len(specs),
        [s.label for s in specs],
    )
    return specs
