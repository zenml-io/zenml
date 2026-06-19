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

"""Data steps: synthesize and prepare robot demonstration trajectories.

The example trains a behavior-cloning policy for a simple 2D reaching task: from
a proprioceptive observation (end-effector position, target position) the policy
predicts the next velocity command an expert would issue. The "demonstrations"
are generated analytically so the example runs anywhere without a robot or a
dataset download, while still exercising the full ZenML artifact flow.
"""

from typing import Annotated, Tuple

import numpy as np
import pandas as pd

from zenml import log_metadata, step

OBS_COLUMNS = ["ee_x", "ee_y", "target_x", "target_y"]
ACTION_COLUMNS = ["vel_x", "vel_y"]


@step
def generate_demonstrations(
    num_episodes: int = 512,
    steps_per_episode: int = 32,
    seed: int = 42,
) -> Annotated[pd.DataFrame, "expert_demonstrations"]:
    """Roll out a scripted expert to collect reaching demonstrations.

    Args:
        num_episodes: Number of demonstration episodes to roll out.
        steps_per_episode: Time steps recorded per episode.
        seed: Random seed for reproducibility.

    Returns:
        A tidy table of (observation, expert action) transitions.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(num_episodes):
        ee = rng.uniform(-1.0, 1.0, size=2)
        target = rng.uniform(-1.0, 1.0, size=2)
        for _ in range(steps_per_episode):
            # Expert command: move toward the target with mild damping + noise.
            action = 0.3 * (target - ee) + rng.normal(0, 0.01, size=2)
            rows.append([*ee, *target, *action])
            ee = ee + action

    df = pd.DataFrame(rows, columns=OBS_COLUMNS + ACTION_COLUMNS)
    log_metadata(
        metadata={
            "num_episodes": num_episodes,
            "num_transitions": len(df),
            "obs_dim": len(OBS_COLUMNS),
            "action_dim": len(ACTION_COLUMNS),
        }
    )
    return df


@step
def prepare_datasets(
    demonstrations: pd.DataFrame,
    val_fraction: float = 0.2,
    seed: int = 42,
) -> Tuple[
    Annotated[pd.DataFrame, "train_set"],
    Annotated[pd.DataFrame, "val_set"],
]:
    """Shuffle and split demonstrations into train/validation sets.

    Args:
        demonstrations: The collected expert transitions.
        val_fraction: Fraction of transitions held out for validation.
        seed: Random seed controlling the shuffle.

    Returns:
        The train and validation splits.
    """
    shuffled = demonstrations.sample(frac=1.0, random_state=seed).reset_index(
        drop=True
    )
    cut = int(len(shuffled) * (1 - val_fraction))
    train_set, val_set = shuffled.iloc[:cut], shuffled.iloc[cut:]
    log_metadata(
        metadata={"train_rows": len(train_set), "val_rows": len(val_set)}
    )
    return train_set, val_set
