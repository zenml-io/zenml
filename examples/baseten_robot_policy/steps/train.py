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

"""Training step: fit the behavior-cloning policy.

This is the GPU-heavy step. In the example stack it is pointed at the Baseten
step operator (see ``run.py``), so it executes as a single-node H100 training
job on Baseten while the rest of the pipeline runs under the local/remote
orchestrator. The step keeps full ZenML semantics: it consumes the train
artifact and produces the fitted policy artifact.
"""

from typing import Annotated, Any, Dict

import numpy as np
import pandas as pd

from steps.data import ACTION_COLUMNS, OBS_COLUMNS
from zenml import log_metadata, step


@step
def train_policy(
    train_set: pd.DataFrame,
    hidden_dim: int = 128,
    epochs: int = 50,
    learning_rate: float = 1e-2,
) -> Annotated[Dict[str, Any], "policy"]:
    """Train a small MLP policy with PyTorch if available, else a linear fit.

    The PyTorch path runs on the GPU when the step executes on Baseten; the
    NumPy least-squares fallback keeps the example runnable on a laptop with no
    deep-learning stack installed.

    Args:
        train_set: Expert transitions to imitate.
        hidden_dim: Width of the policy's hidden layer (PyTorch path).
        epochs: Training epochs (PyTorch path).
        learning_rate: Optimizer learning rate (PyTorch path).

    Returns:
        A serializable policy: framework tag plus learned weights.
    """
    obs = train_set[OBS_COLUMNS].to_numpy(dtype="float32")
    actions = train_set[ACTION_COLUMNS].to_numpy(dtype="float32")

    try:
        import torch
        from torch import nn

        device = "cuda" if torch.cuda.is_available() else "cpu"
        x = torch.from_numpy(obs).to(device)
        y = torch.from_numpy(actions).to(device)
        model = nn.Sequential(
            nn.Linear(obs.shape[1], hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, actions.shape[1]),
        ).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=learning_rate)
        loss_fn = nn.MSELoss()
        final_loss = 0.0
        for _ in range(epochs):
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            final_loss = float(loss.item())

        log_metadata(
            metadata={
                "framework": "pytorch",
                "device": device,
                "gpu": torch.cuda.get_device_name(0)
                if device == "cuda"
                else "cpu",
                "epochs": epochs,
                "final_train_loss": final_loss,
            }
        )
        state = {k: v.cpu().numpy() for k, v in model.state_dict().items()}
        return {
            "framework": "pytorch",
            "hidden_dim": hidden_dim,
            "state": state,
        }
    except ImportError:
        # Closed-form linear behavior cloning: action ~= W @ obs + b.
        x_aug = np.hstack([obs, np.ones((len(obs), 1), dtype="float32")])
        weights, *_ = np.linalg.lstsq(x_aug, actions, rcond=None)
        residual = obs @ weights[:-1] + weights[-1] - actions
        log_metadata(
            metadata={
                "framework": "numpy-linear",
                "final_train_loss": float((residual**2).mean()),
            }
        )
        return {"framework": "linear", "weights": weights}
