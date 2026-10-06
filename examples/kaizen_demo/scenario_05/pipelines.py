# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Train customer models and evaluate their held-out predictions."""

from build_settings import create_docker_settings

from zenml import Model, pipeline

from .steps import evaluate_customer_model, fit_customer_model


@pipeline(
    model=Model(
        name="customer-retention",
        description="Identify customers who may benefit from a follow-up.",
        limitations="Trained on synthetic customer activity for demonstration.",
    ),
    settings={"docker": create_docker_settings()},
)
def customer_model_training(
    sample_count: int = 400, random_seed: int = 23
) -> None:
    """Train a classifier and retain its independent evaluation dataset.

    Args:
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for data generation and the train/test split.
    """
    fit_customer_model(sample_count=sample_count, random_seed=random_seed)


@pipeline(
    enable_cache=False,
    settings={"docker": create_docker_settings()},
)
def customer_model_evaluation(training_run_id: str | None = None) -> None:
    """Evaluate the model from a completed customer training run.

    Args:
        training_run_id: Full training run UUID for a manual evaluation. When
            omitted, use the upstream run recorded by the platform trigger.
    """
    evaluate_customer_model(training_run_id=training_run_id)
