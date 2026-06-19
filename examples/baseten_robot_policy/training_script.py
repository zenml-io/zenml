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

"""Behavior-cloning training entry point run by the Baseten `CommandStep`.

This is the *opaque command* the step operator executes on Baseten, launched as:

* single node  -> ``python training_script.py``
* multi node   -> ``torchrun`` across Baseten-provisioned nodes, reading the
  topology Baseten injects (``BT_GROUP_SIZE``, ``BT_NODE_RANK``, ``BT_NUM_GPUS``).

A `CommandStep` runs as an opaque job and cannot receive ZenML artifacts, so the
dataset is regenerated here from the same ``SEED``/``N_SAMPLES`` the upstream
`prepare_training_run` step used. `make_demonstrations` is the single source of
truth for that data: the prep step imports it, guaranteeing both sides train on
exactly the same demonstrations (production jobs would instead stream the
versioned dataset from a shared bucket).
"""

import os
from typing import Tuple

import numpy as np


def make_demonstrations(
    seed: int, n_samples: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate deterministic 2D-reaching expert demonstrations.

    From an observation (end-effector position, target position) the expert
    issues a velocity command that moves toward the target. Generation is fully
    determined by ``seed`` so it can be reproduced identically anywhere.

    Args:
        seed: Random seed controlling the demonstrations.
        n_samples: Number of (observation, action) transitions.

    Returns:
        A ``(observations, actions)`` pair of float32 arrays.
    """
    rng = np.random.default_rng(seed)
    ee = rng.uniform(-1.0, 1.0, size=(n_samples, 2))
    target = rng.uniform(-1.0, 1.0, size=(n_samples, 2))
    observations = np.hstack([ee, target]).astype("float32")
    actions = (0.3 * (target - ee)).astype("float32")
    return observations, actions


def main() -> None:
    """Train a small reaching policy and report per-node metrics."""
    import torch
    from torch import nn

    seed = int(os.environ.get("SEED", "42"))
    n_samples = int(os.environ.get("N_SAMPLES", "8192"))
    epochs = int(os.environ.get("EPOCHS", "200"))
    node_rank = int(
        os.environ.get("BT_NODE_RANK", os.environ.get("RANK", "0"))
    )
    world_size = int(
        os.environ.get("BT_GROUP_SIZE", os.environ.get("WORLD_SIZE", "1"))
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)

    obs_np, act_np = make_demonstrations(seed, n_samples)
    obs = torch.from_numpy(obs_np).to(device)
    expert = torch.from_numpy(act_np).to(device)

    model = nn.Sequential(nn.Linear(4, 128), nn.Tanh(), nn.Linear(128, 2)).to(
        device
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    loss_fn = nn.MSELoss()

    loss = torch.tensor(0.0)
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(model(obs), expert)
        loss.backward()
        opt.step()

    tag = f"[node {node_rank + 1}/{world_size}]"
    gpu = torch.cuda.get_device_name(0) if device == "cuda" else "cpu"
    print(
        f"{tag} device={device} ({gpu}) samples={n_samples} epochs={epochs} "
        f"final_loss={float(loss):.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
