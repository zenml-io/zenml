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

"""Upstream preparation step for the robot policy training pipeline.

This regular step runs in the orchestrator environment (locally in the demo). It
generates and versions the demonstration dataset as a ZenML artifact so it is
inspectable and reproducible in the dashboard. Because the downstream training
runs as an opaque Baseten `CommandStep` (which cannot receive ZenML artifacts),
the command regenerates the identical dataset from the same ``seed`` using the
shared `make_demonstrations` routine — so both sides provably train on the same
data without passing an artifact between them.
"""

from typing import Annotated

import pandas as pd
from training_script import make_demonstrations

from zenml import log_metadata, step

OBS_COLUMNS = ["ee_x", "ee_y", "target_x", "target_y"]
ACTION_COLUMNS = ["vel_x", "vel_y"]


@step
def prepare_training_run(
    seed: int = 42,
    num_samples: int = 8192,
) -> Annotated[pd.DataFrame, "expert_demonstrations"]:
    """Generate and version the demonstration dataset for the run.

    Args:
        seed: Random seed; the training command reuses it to reproduce the exact
            same demonstrations.
        num_samples: Number of (observation, action) transitions to generate.

    Returns:
        The demonstrations as a tidy table, stored as a ZenML artifact.
    """
    observations, actions = make_demonstrations(seed, num_samples)
    demonstrations = pd.DataFrame(
        data=list(map(list, observations)),
        columns=OBS_COLUMNS,
    )
    demonstrations[ACTION_COLUMNS] = actions

    log_metadata(
        metadata={
            "task": "2d-reaching",
            "seed": seed,
            "num_samples": int(num_samples),
            "obs_dim": len(OBS_COLUMNS),
            "action_dim": len(ACTION_COLUMNS),
        }
    )
    return demonstrations
