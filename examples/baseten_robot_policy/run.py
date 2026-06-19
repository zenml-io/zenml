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

"""Run the Baseten robot policy example.

Examples:
    # Run the training command locally (no Baseten) for a quick smoke test:
    python run.py --local

    # Single-node training on Baseten (one H100):
    python run.py --step-operator baseten_operator

    # Multi-node distributed training (requires the org to have multi-node
    # instance types enabled, see the README):
    python run.py --step-operator baseten_operator --node-count 4 --gpu-count 8
"""

from typing import Optional

import click
from pipelines import robot_policy_pipeline

from zenml import Model


@click.command()
@click.option(
    "--step-operator",
    default=None,
    help="Name of the Baseten step operator to run the training command on. "
    "Omit (or use --local) to run it in the orchestrator environment.",
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Force local execution (ignores --step-operator).",
)
@click.option(
    "--accelerator", default="H100", help="Baseten accelerator type."
)
@click.option(
    "--node-count", default=1, help="Number of nodes (>1 = multi-node)."
)
@click.option("--gpu-count", default=1, help="GPUs per node.")
@click.option("--epochs", default=200, help="Training epochs.")
def main(
    step_operator: Optional[str],
    local: bool,
    accelerator: str,
    node_count: int,
    gpu_count: int,
    epochs: int,
) -> None:
    """Configure and launch the robot policy pipeline."""
    operator = None if local else step_operator
    model = Model(
        name="reaching_policy",
        description="Behavior-cloning policy for a 2D reaching task.",
        tags=["robotics", "behavior-cloning", "baseten"],
    )

    robot_policy_pipeline.with_options(model=model)(
        step_operator=operator,
        accelerator=accelerator,
        node_count=node_count,
        gpu_count=gpu_count,
        epochs=epochs,
    )


if __name__ == "__main__":
    main()
