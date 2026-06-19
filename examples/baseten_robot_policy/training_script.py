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

This is the *opaque command* the step operator executes on Baseten. It is
written to be launch-agnostic:

* single node  -> run directly with ``python training_script.py``
* multi node   -> launched by ``torchrun`` across Baseten-provisioned nodes,
  reading the rank/world topology Baseten injects (``BT_GROUP_SIZE``,
  ``BT_NODE_RANK``, ``BT_NUM_GPUS``) plus the ``torchrun`` standard env.

A real robotics job would stream demonstrations from a shared bucket; here we
synthesize them so the command is fully self-contained (CommandSteps do not
exchange ZenML artifacts).
"""

import os


def main() -> None:
    """Train a small reaching policy and report per-node metrics."""
    import torch
    from torch import nn

    node_rank = int(
        os.environ.get("BT_NODE_RANK", os.environ.get("RANK", "0"))
    )
    world_size = int(
        os.environ.get("BT_GROUP_SIZE", os.environ.get("WORLD_SIZE", "1"))
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)

    # Synthetic 2D reaching demonstrations: predict the expert velocity command
    # from (end-effector position, target position).
    n = 8192
    ee = torch.rand(n, 2) * 2 - 1
    target = torch.rand(n, 2) * 2 - 1
    obs = torch.cat([ee, target], dim=1).to(device)
    expert = (0.3 * (target - ee)).to(device)

    model = nn.Sequential(nn.Linear(4, 128), nn.Tanh(), nn.Linear(128, 2)).to(
        device
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    loss_fn = nn.MSELoss()

    epochs = int(os.environ.get("EPOCHS", "200"))
    loss = torch.tensor(0.0)
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(model(obs), expert)
        loss.backward()
        opt.step()

    tag = f"[node {node_rank + 1}/{world_size}]"
    gpu = torch.cuda.get_device_name(0) if device == "cuda" else "cpu"
    print(
        f"{tag} device={device} ({gpu}) final_loss={float(loss):.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
