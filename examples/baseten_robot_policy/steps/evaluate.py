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

"""Evaluation and promotion steps for the behavior-cloning policy."""

from typing import Annotated, Any, Dict

import numpy as np
import pandas as pd

from steps.data import ACTION_COLUMNS, OBS_COLUMNS
from zenml import get_step_context, log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


def _predict(policy: Dict[str, Any], obs: np.ndarray) -> np.ndarray:
    """Run the learned policy forward on a batch of observations."""
    if policy["framework"] == "linear":
        weights = policy["weights"]
        return obs @ weights[:-1] + weights[-1]

    import torch
    from torch import nn

    hidden_dim = policy["hidden_dim"]
    model = nn.Sequential(
        nn.Linear(obs.shape[1], hidden_dim),
        nn.Tanh(),
        nn.Linear(hidden_dim, len(ACTION_COLUMNS)),
    )
    model.load_state_dict(
        {k: torch.from_numpy(v) for k, v in policy["state"].items()}
    )
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(obs.astype("float32"))).numpy()


@step
def evaluate_policy(
    policy: Dict[str, Any],
    val_set: pd.DataFrame,
) -> Annotated[float, "val_mse"]:
    """Measure how closely the policy reproduces expert actions.

    Args:
        policy: The trained policy artifact.
        val_set: Held-out expert transitions.

    Returns:
        Mean squared error between predicted and expert actions.
    """
    obs = val_set[OBS_COLUMNS].to_numpy(dtype="float32")
    expert = val_set[ACTION_COLUMNS].to_numpy(dtype="float32")
    mse = float(((_predict(policy, obs) - expert) ** 2).mean())
    log_metadata(metadata={"val_mse": mse, "framework": policy["framework"]})
    logger.info("Validation MSE: %.6f", mse)
    return mse


@step
def promote_policy(val_mse: float, threshold: float = 0.05) -> bool:
    """Promote the model version to production when it clears the bar.

    Args:
        val_mse: Validation MSE from the evaluation step.
        threshold: Maximum MSE allowed for promotion.

    Returns:
        Whether the policy was promoted.
    """
    promoted = val_mse <= threshold
    if promoted:
        model = get_step_context().model
        model.set_stage("production", force=True)
        logger.info("Policy promoted to production (val_mse=%.6f).", val_mse)
    else:
        logger.warning(
            "Policy NOT promoted: val_mse=%.6f exceeds threshold=%.6f.",
            val_mse,
            threshold,
        )
    log_metadata(metadata={"promoted": promoted})
    return promoted
