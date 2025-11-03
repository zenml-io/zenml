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

"""Data generation step for churn prediction."""

from typing import Annotated, Tuple

import numpy as np
import pandas as pd

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def generate_churn_data(
    num_samples: int = 1000, random_seed: int = 42
) -> Tuple[
    Annotated[pd.DataFrame, "features"], Annotated[pd.Series, "target"]
]:
    """Generate synthetic customer churn data for training.

    Args:
        num_samples: Number of samples to generate
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of features DataFrame and target Series
    """
    logger.info(f"Generating {num_samples} synthetic churn samples...")

    np.random.seed(random_seed)

    data = {
        "account_length": np.random.normal(100, 40, num_samples).astype(int),
        "customer_service_calls": np.random.poisson(1.5, num_samples),
        "monthly_charges": np.random.normal(50, 20, num_samples),
        "total_charges": np.random.normal(1500, 800, num_samples),
        "has_internet_service": np.random.choice(
            [0, 1], num_samples, p=[0.3, 0.7]
        ),
        "has_phone_service": np.random.choice(
            [0, 1], num_samples, p=[0.1, 0.9]
        ),
        "contract_length": np.random.choice(
            [1, 12, 24], num_samples, p=[0.5, 0.3, 0.2]
        ),
        "payment_method_electronic": np.random.choice(
            [0, 1], num_samples, p=[0.4, 0.6]
        ),
    }

    data["account_length"] = np.maximum(data["account_length"], 1)
    data["monthly_charges"] = np.maximum(data["monthly_charges"], 10)
    data["total_charges"] = np.maximum(data["total_charges"], 50)

    features = pd.DataFrame(data)

    churn_prob = (
        0.1  # base churn rate
        + 0.4 * (features["customer_service_calls"] > 3)  # high service calls
        + 0.3 * (features["contract_length"] == 1)  # month-to-month
        + 0.2 * (features["monthly_charges"] > 70)  # high charges
        + 0.1
        * (
            features["payment_method_electronic"] == 1
        )  # electronic payment (slight negative)
        - 0.2
        * (
            features["has_internet_service"] == 1
        )  # internet service (retention)
    )

    churn_prob = np.clip(
        churn_prob + np.random.normal(0, 0.1, num_samples), 0, 1
    )
    target = np.random.binomial(1, churn_prob, num_samples)

    logger.info(
        f"Generated data with {target.sum()} churned customers ({target.mean():.2%} churn rate)"
    )

    return features, pd.Series(target, name="churn")
