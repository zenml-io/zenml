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
"""Tests for trial identities and shard packing (no Harbor required)."""

import random

import pytest

from zenml.integrations.harbor.models import TaskRef
from zenml.integrations.harbor.utils import pack_shards, trial_identity

TASK_A = TaskRef(path="/tasks/a")
TASK_B = TaskRef(
    git_url="https://github.com/org/tasks",
    git_commit_id="deadbeef",
    path="tasks/b",
)


def test_trial_identity_is_deterministic() -> None:
    """Identical coordinates hash identically."""
    assert trial_identity(TASK_A, "oracle", None, 0) == trial_identity(
        TaskRef(path="/tasks/a"), "oracle", None, 0
    )


@pytest.mark.parametrize(
    "other",
    [
        (TASK_B, "oracle", None, 0),
        (TASK_A, "nop", None, 0),
        (TASK_A, "oracle", "gpt-x", 0),
        (TASK_A, "oracle", None, 1),
    ],
)
def test_trial_identity_distinguishes_every_field(other) -> None:
    """Changing any coordinate changes the identity."""
    assert trial_identity(TASK_A, "oracle", None, 0) != trial_identity(*other)


def test_trial_identity_ignores_resolver_metadata() -> None:
    """Dataset-resolved and direct refs to the same pin hash identically.

    The dataset resolver stamps `source`/`name`/`ref` onto its TaskRefs;
    a direct git+ spec carries none of them. Identities must join on the
    pin coordinates, not on how the task was specified.
    """
    direct = TaskRef.parse("git+https://github.com/org/tasks@deadbeef:tasks/b")
    resolved = TaskRef(
        git_url="https://github.com/org/tasks",
        git_commit_id="deadbeef",
        path="tasks/b",
        name="b",
        ref="main",
        source="terminal-bench",
    )
    assert trial_identity(direct, "oracle", None, 0) == trial_identity(
        resolved, "oracle", None, 0
    )


def test_trial_identity_distinguishes_package_tasks() -> None:
    """Registry package tasks (name/ref only) must not collide.

    Their TaskRefs carry neither a path nor a git URL; an empty
    canonical string would give every package task the same identity.
    """
    a = TaskRef(name="laude/task-a", ref="sha256:aaa")
    b = TaskRef(name="laude/task-b", ref="sha256:bbb")
    assert trial_identity(a, "oracle", None, 0) != trial_identity(
        b, "oracle", None, 0
    )


def test_trial_identity_rejects_unidentifiable_task() -> None:
    """A ref with no coordinates at all cannot get an identity."""
    with pytest.raises(ValueError, match="no identifying coordinates"):
        trial_identity(TaskRef(), "oracle", None, 0)


def test_trial_identity_distinguishes_agent_config() -> None:
    """Same agent+model with different kwargs/env must not collide."""
    base = trial_identity(
        TASK_A, "terminus", "gpt-5", 0, agent_kwargs={"temperature": 0.0}
    )
    assert base != trial_identity(
        TASK_A, "terminus", "gpt-5", 0, agent_kwargs={"temperature": 1.0}
    )
    assert base != trial_identity(
        TASK_A,
        "terminus",
        "gpt-5",
        0,
        agent_kwargs={"temperature": 0.0},
        agent_env={"KEY": "value"},
    )
    # Empty configs hash like omitted configs.
    assert trial_identity(
        TASK_A, "oracle", None, 0, agent_kwargs={}, agent_env={}
    ) == trial_identity(TASK_A, "oracle", None, 0)


def test_pack_shards_distinguishes_agent_configs() -> None:
    """Two configs of the same agent yield distinct shards/identities."""
    shards = pack_shards(
        tasks=[TASK_A],
        agents=[
            {"name": "terminus", "model_name": "gpt-5", "kwargs": {"t": 0}},
            {"name": "terminus", "model_name": "gpt-5", "kwargs": {"t": 1}},
        ],
        trials_per_cell=2,
        trials_per_step=2,
    )
    assert len(shards) == 2
    assert shards[0].shard_id != shards[1].shard_id
    assert not set(shards[0].trial_identities) & set(
        shards[1].trial_identities
    )


def test_pack_shards_single_cell_per_shard() -> None:
    """No shard ever mixes (task, agent, model) cells."""
    shards = pack_shards(
        tasks=[TASK_A, TASK_B],
        agents=[{"name": "oracle"}, {"name": "nop"}],
        trials_per_cell=3,
        trials_per_step=2,
    )
    for shard in shards:
        assert len(shard.trial_indices) <= 2
        assert len(shard.trial_indices) == len(shard.trial_identities)
    cells = {(s.task.to_string(), s.agent_name, s.model_name) for s in shards}
    assert len(cells) == 4


def test_pack_shards_counts_and_remainders() -> None:
    """3 tasks x 2 agents x 5 trials at cap 2 pack into 18 shards."""
    tasks = [TASK_A, TASK_B, TaskRef(path="/tasks/c")]
    agents = [{"name": "oracle"}, {"name": "nop"}]
    shards = pack_shards(
        tasks=tasks, agents=agents, trials_per_cell=5, trials_per_step=2
    )
    assert len(shards) == 18
    sizes = sorted(len(s.trial_indices) for s in shards)
    assert sizes == [1] * 6 + [2] * 12
    all_identities = [i for s in shards for i in s.trial_identities]
    assert len(all_identities) == len(set(all_identities)) == 30


def test_pack_shards_cap_larger_than_cell() -> None:
    """A cap above the cell size yields one shard per cell."""
    shards = pack_shards(
        tasks=[TASK_A],
        agents=[{"name": "oracle"}],
        trials_per_cell=3,
        trials_per_step=10,
    )
    assert len(shards) == 1
    assert shards[0].trial_indices == [0, 1, 2]


def test_pack_shards_is_deterministic_under_input_order() -> None:
    """Shuffled inputs produce the identical shard list."""
    tasks = [TASK_A, TASK_B, TaskRef(path="/tasks/c")]
    agents = [
        {"name": "oracle"},
        {"name": "claude-code", "model_name": "claude-fable-5"},
    ]
    reference = pack_shards(
        tasks=tasks, agents=agents, trials_per_cell=4, trials_per_step=3
    )
    for seed in range(3):
        shuffled_tasks = tasks.copy()
        shuffled_agents = agents.copy()
        random.Random(seed).shuffle(shuffled_tasks)
        random.Random(seed).shuffle(shuffled_agents)
        assert (
            pack_shards(
                tasks=shuffled_tasks,
                agents=shuffled_agents,
                trials_per_cell=4,
                trials_per_step=3,
            )
            == reference
        )


def test_pack_shards_carries_agent_details() -> None:
    """Model, kwargs and env flow into the shard spec."""
    shards = pack_shards(
        tasks=[TASK_A],
        agents=[
            {
                "name": "claude-code",
                "model_name": "claude-fable-5",
                "kwargs": {"budget": 5},
                "env": {"KEY": "value"},
            }
        ],
        trials_per_cell=1,
        trials_per_step=1,
    )
    assert shards[0].agent_name == "claude-code"
    assert shards[0].model_name == "claude-fable-5"
    assert shards[0].agent_kwargs == {"budget": 5}
    assert shards[0].agent_env == {"KEY": "value"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trials_per_cell": 0},
        {"trials_per_step": 0},
    ],
)
def test_pack_shards_rejects_non_positive_counts(kwargs) -> None:
    """Non-positive counts are rejected."""
    params = dict(
        tasks=[TASK_A],
        agents=[{"name": "oracle"}],
        trials_per_cell=1,
        trials_per_step=1,
    )
    params.update(kwargs)
    with pytest.raises(ValueError):
        pack_shards(**params)


def test_pack_shards_rejects_unnamed_agent() -> None:
    """Agent specs without a name are rejected."""
    with pytest.raises(ValueError, match="missing a 'name'"):
        pack_shards(
            tasks=[TASK_A],
            agents=[{"model_name": "gpt-x"}],
            trials_per_cell=1,
            trials_per_step=1,
        )
