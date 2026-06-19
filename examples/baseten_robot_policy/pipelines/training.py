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

"""The robot policy training pipeline (Baseten `CommandStep` variant).

    prepare_training_run            # regular step, runs in the orchestrator
              |
              v
        train (CommandStep)         # opaque GPU command, runs on Baseten

The training step is a `CommandStep` rather than a regular `@step` on purpose:
it runs on a stock public PyTorch image (no custom image required) and, for
`node_count > 1`, lets `torchrun` own the distributed launch across the nodes
Baseten provisions. See the README for why this is the recommended Baseten
pattern and which modes a Baseten organization must have enabled.
"""

import base64
from pathlib import Path
from typing import List, Optional

from steps import prepare_training_run

from zenml import CommandStep, pipeline
from zenml.config import DockerSettings, ResourceSettings
from zenml.integrations.baseten.flavors import BasetenStepOperatorSettings

# Stock, publicly pullable base image — no custom image is built or pushed.
PUBLIC_TRAINING_IMAGE = "pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime"

_SCRIPT_PATH = Path(__file__).parents[1] / "training_script.py"


def _build_command(node_count: int) -> List[str]:
    """Build the opaque training command for the `CommandStep`.

    The training script is embedded (base64) so it runs on the stock image
    without baking a custom image: the command materializes it on the node and
    then launches it directly (single node) or through `torchrun` (multi node).

    Args:
        node_count: Number of Baseten nodes the job will run on.

    Returns:
        The command argv for the `CommandStep`.
    """
    encoded = base64.b64encode(_SCRIPT_PATH.read_bytes()).decode()
    materialize = (
        f"import base64,pathlib;"
        f"pathlib.Path('/tmp/train.py').write_bytes("
        f"base64.b64decode('{encoded}'))"
    )
    if node_count > 1:
        launch = (
            "torchrun --nnodes=$BT_GROUP_SIZE --node-rank=$BT_NODE_RANK "
            "--master-addr=$BT_LEADER_ADDR --master-port=29500 "
            "--nproc-per-node=$BT_NUM_GPUS /tmp/train.py"
        )
    else:
        launch = "python /tmp/train.py"
    return ["bash", "-lc", f'python -c "{materialize}" && {launch}']


@pipeline
def robot_policy_pipeline(
    step_operator: Optional[str] = None,
    accelerator: str = "H100",
    node_count: int = 1,
    gpu_count: int = 1,
    num_episodes: int = 512,
    epochs: int = 200,
) -> None:
    """Prepare a training run and execute it as a Baseten job.

    Args:
        step_operator: Name of the Baseten step operator. If None, the command
            runs in the orchestrator environment (used by the local smoke test).
        accelerator: Baseten accelerator type for the job (e.g. 'H100').
        node_count: Number of nodes; > 1 launches multi-node training.
        gpu_count: GPUs per node.
        num_episodes: Demonstration episodes to train on.
        epochs: Training epochs for the policy network.
    """
    config = prepare_training_run(num_episodes=num_episodes, epochs=epochs)

    settings: dict = {"resources": ResourceSettings(gpu_count=gpu_count)}
    if step_operator:
        settings["step_operator"] = BasetenStepOperatorSettings(
            accelerator=accelerator, node_count=node_count
        )
        # skip_build => Baseten pulls the public image directly; no custom
        # image is built or pushed.
        settings["docker"] = DockerSettings(
            skip_build=True, parent_image=PUBLIC_TRAINING_IMAGE
        )

    train = CommandStep(
        command=_build_command(node_count),
        step_operator=step_operator,
        settings=settings,
    )
    train(after=config)
