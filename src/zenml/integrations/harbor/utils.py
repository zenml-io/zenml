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
"""Utilities for expanding Harbor eval campaigns into shards."""

import hashlib
import json
from typing import Any, Dict, List, Optional

from zenml.integrations.harbor.models import HarborShardSpec, TaskRef


def trial_identity(
    task: TaskRef,
    agent_name: str,
    model_name: Optional[str],
    trial_index: int,
    agent_kwargs: Optional[Dict[str, Any]] = None,
    agent_env: Optional[Dict[str, str]] = None,
) -> str:
    """Stable identity hash for one trial of a campaign.

    This is the join key for comparing trials across pipeline runs
    (baselines, regressions): two trials with the same identity attempted
    the same pinned task with the same full agent configuration —
    including kwargs and env, so e.g. two temperature settings of the
    same agent never collide.

    The task enters the hash as its canonical pin coordinates
    (``TaskRef.to_string()``), not the full ref: resolver metadata like
    ``source`` or ``name`` varies with how the task was specified
    (dataset expansion vs. a direct ``git+`` ref) and must not fragment
    identities for the byte-identical pinned task. Local-path tasks
    hash as the given path, which stays machine-specific — the
    content-addressed ``task_checksum`` on the trial result is the
    complement for joining those.

    Args:
        task: The task the trial runs.
        agent_name: The Harbor agent attempting the task.
        model_name: The model the agent uses, if pinned.
        trial_index: Position of the trial within its campaign cell.
        agent_kwargs: Extra keyword arguments configured on the agent.
        agent_env: Environment variables configured on the agent.

    Returns:
        A sha256 hex digest over the canonical trial coordinates.
    """
    payload = json.dumps(
        {
            "task": task.to_string(),
            "agent_name": agent_name,
            "model_name": model_name,
            "trial_index": trial_index,
            "agent_kwargs": agent_kwargs or {},
            "agent_env": agent_env or {},
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def pack_shards(
    tasks: List[TaskRef],
    agents: List[Dict[str, Any]],
    trials_per_cell: int,
    trials_per_step: int,
) -> List[HarborShardSpec]:
    """Expand a campaign matrix into deterministic, single-cell shards.

    Every shard holds trials of exactly one (task, agent, model) cell —
    never a mix — so a failed shard invalidates the narrowest possible
    slice of the campaign, and each shard translates 1:1 into a Harbor
    job with ``n_attempts == len(trial_indices)``. Cells with more than
    ``trials_per_step`` trials are split into multiple shards; the last
    shard of a cell may hold the remainder. Cells are sorted canonically
    before packing so the same campaign always produces the same shard
    list (and therefore stable step-cache keys).

    Args:
        tasks: The tasks in the campaign.
        agents: Agent specifications, each a dict with at least ``name``
            and optionally ``model_name``, ``kwargs`` and ``env``.
        trials_per_cell: Number of trials per (task, agent) combination.
        trials_per_step: Maximum number of trials per shard, i.e. per
            mapped pipeline step.

    Returns:
        The ordered list of shard specifications.

    Raises:
        ValueError: If an agent specification has no name, or a count
            parameter is not positive.
    """
    if trials_per_cell < 1:
        raise ValueError("trials_per_cell must be at least 1.")
    if trials_per_step < 1:
        raise ValueError("trials_per_step must be at least 1.")
    for agent in agents:
        if not agent.get("name"):
            raise ValueError(
                f"Agent specification {agent!r} is missing a 'name'."
            )

    cells = sorted(
        ((task, agent) for task in tasks for agent in agents),
        key=lambda cell: (
            cell[0].to_string(),
            cell[1]["name"],
            cell[1].get("model_name") or "",
            json.dumps(cell[1].get("kwargs") or {}, sort_keys=True),
            json.dumps(cell[1].get("env") or {}, sort_keys=True),
        ),
    )

    shards = []
    for task, agent in cells:
        model_name = agent.get("model_name")
        identities = [
            trial_identity(
                task,
                agent["name"],
                model_name,
                index,
                agent_kwargs=agent.get("kwargs") or {},
                agent_env=agent.get("env") or {},
            )
            for index in range(trials_per_cell)
        ]
        for start in range(0, trials_per_cell, trials_per_step):
            indices = list(
                range(start, min(start + trials_per_step, trials_per_cell))
            )
            shard_identities = [identities[i] for i in indices]
            shard_id = hashlib.sha256(
                json.dumps(shard_identities).encode("utf-8")
            ).hexdigest()
            shards.append(
                HarborShardSpec(
                    shard_id=shard_id,
                    task=task,
                    agent_name=agent["name"],
                    model_name=model_name,
                    agent_kwargs=agent.get("kwargs") or {},
                    agent_env=agent.get("env") or {},
                    trial_indices=indices,
                    trial_identities=shard_identities,
                )
            )
    return shards
