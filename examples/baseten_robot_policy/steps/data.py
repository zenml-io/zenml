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

This regular step runs in the orchestrator environment (locally in the demo)
and produces the training configuration that the downstream Baseten training
job consumes. It exists to show a connected pipeline: a normal ZenML step
feeding into a GPU `CommandStep` that runs on Baseten.
"""

from typing import Annotated, Dict

from zenml import log_metadata, step


@step
def prepare_training_run(
    num_episodes: int = 512,
    epochs: int = 200,
) -> Annotated[Dict[str, int], "training_config"]:
    """Assemble the behavior-cloning training configuration.

    In a real robotics setup this step would version the demonstration dataset
    and write it to the artifact store / a shared bucket that the (opaque)
    training command then reads. Here it records the run configuration as
    metadata and passes it downstream.

    Args:
        num_episodes: Number of demonstration episodes the policy trains on.
        epochs: Training epochs for the policy network.

    Returns:
        The training configuration consumed by the training job.
    """
    config = {"num_episodes": num_episodes, "epochs": epochs}
    log_metadata(metadata={**config, "task": "2d-reaching"})
    return config
