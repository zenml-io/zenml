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

"""The robot policy training pipeline.

Wires the steps into a connected DAG:

    generate_demonstrations
              |
        prepare_datasets ---> (train_set, val_set)
              |                      |
        train_policy (Baseten) <-----+
              |
        evaluate_policy <----- val_set
              |
        promote_policy
"""

from steps import (
    evaluate_policy,
    generate_demonstrations,
    prepare_datasets,
    promote_policy,
    train_policy,
)

from zenml import pipeline


@pipeline
def robot_policy_pipeline(
    num_episodes: int = 512,
    epochs: int = 50,
    promotion_threshold: float = 0.05,
) -> None:
    """Train and conditionally promote a reaching policy.

    Args:
        num_episodes: Demonstration episodes to generate.
        epochs: Training epochs for the policy network.
        promotion_threshold: Max validation MSE allowed for promotion.
    """
    demonstrations = generate_demonstrations(num_episodes=num_episodes)
    train_set, val_set = prepare_datasets(demonstrations)
    policy = train_policy(train_set, epochs=epochs)
    val_mse = evaluate_policy(policy, val_set)
    promote_policy(val_mse, threshold=promotion_threshold)
