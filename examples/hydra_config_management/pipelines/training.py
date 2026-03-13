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
"""Training pipeline driven by Hydra configuration.

Hydra controls WHAT (hyperparameters, model config, data config).
ZenML controls WHERE/WHEN (orchestration, caching, artifact tracking).
"""

from steps import evaluate_model, train_model

from zenml import pipeline


@pipeline
def hydra_training_pipeline(
    learning_rate: float = 0.001,
    batch_size: int = 64,
    hidden_dim: int = 32,
    max_epochs: int = 10,
) -> None:
    """Train and evaluate a FashionMNIST classifier.

    All parameters come from Hydra config (conf/config.yaml) and can be
    overridden from the CLI. ZenML handles orchestration, caching, and
    artifact tracking.

    Args:
        learning_rate: Learning rate for the Adam optimizer
        batch_size: Training batch size
        hidden_dim: Number of filters in the first conv layer
        max_epochs: Maximum number of training epochs

    Pipeline DAG:
        train_model -> evaluate_model
    """
    model = train_model(
        learning_rate=learning_rate,
        batch_size=batch_size,
        hidden_dim=hidden_dim,
        max_epochs=max_epochs,
    )

    evaluate_model(
        model=model,
        batch_size=batch_size,
    )
