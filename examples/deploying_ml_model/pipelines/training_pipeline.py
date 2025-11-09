# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
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

"""Churn prediction training pipeline."""

from typing import Tuple

from sklearn.pipeline import Pipeline
from steps import generate_churn_data, train_churn_model

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
        )
    },
)
def churn_training_pipeline(
    num_samples: int = 1000, test_size: float = 0.2, random_state: int = 42
) -> Tuple[Pipeline, float]:
    """Train a customer churn prediction model.

    This pipeline generates synthetic customer data, trains a Random Forest
    classifier, and returns the trained model with its accuracy score.

    Args:
        num_samples: Number of synthetic customers to generate for training
        test_size: Proportion of data to use for testing (0.0 to 1.0)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of trained model pipeline and accuracy score
    """
    # Generate synthetic customer data
    features, target = generate_churn_data(
        num_samples=num_samples, random_seed=random_state
    )

    # Train the churn prediction model
    model, accuracy = train_churn_model(
        features=features,
        target=target,
        test_size=test_size,
        random_state=random_state,
    )

    return model, accuracy
