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

"""Train and serve a customer risk classifier."""

from typing import Annotated, Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from zenml import (
    ArtifactConfig,
    get_step_context,
    log_metadata,
    pipeline,
    step,
)
from zenml.client import Client
from zenml.config import DeploymentSettings, DockerSettings
from zenml.logger import get_logger

MODEL_ARTIFACT = "customer_risk_model"
logger = get_logger(__name__)


@step
def fit_risk_model(
    sample_count: int = 320, random_seed: int = 41
) -> Annotated[Pipeline, ArtifactConfig(name=MODEL_ARTIFACT)]:
    """Fit a classifier on a reproducible customer sample.

    Args:
        sample_count: Number of customer records to generate.
        random_seed: Seed for the training sample.

    Returns:
        Fitted preprocessing and classification pipeline.

    Raises:
        ValueError: If the requested sample is too small.
    """
    if sample_count < 100:
        raise ValueError("At least 100 customer records are required.")
    rng = np.random.default_rng(random_seed)
    features = pd.DataFrame(
        {
            "monthly_charges": rng.uniform(20, 120, sample_count),
            "account_length": rng.integers(1, 61, sample_count),
            "support_calls": rng.integers(0, 7, sample_count),
        }
    )
    target = (
        0.05 * features["monthly_charges"]
        - 0.12 * features["account_length"]
        + 0.9 * features["support_calls"]
        > 3.0
    ).astype(int)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("classify", LogisticRegression(random_state=random_seed)),
        ]
    )
    model.fit(features, target)
    log_metadata(
        metadata={
            "sample_count": sample_count,
            "feature_names": list(features.columns),
            "positive_fraction": float(target.mean()),
        }
    )
    return model


@pipeline(settings={"docker": DockerSettings(requirements="requirements.txt")})
def customer_risk_training(
    sample_count: int = 320, random_seed: int = 41
) -> None:
    """Train the customer risk model.

    Args:
        sample_count: Number of synthetic customer records.
        random_seed: Seed for reproducible training.
    """
    fit_risk_model(sample_count=sample_count, random_seed=random_seed)


def initialize_risk_service() -> dict[str, Any]:
    """Load the customer risk model for the lifetime of a deployment.

    Returns:
        The fitted model and its artifact version identifier.

    Raises:
        TypeError: If the selected artifact is not a sklearn pipeline.
    """
    artifact = Client().get_artifact_version(MODEL_ARTIFACT)
    model = artifact.load()
    if not isinstance(model, Pipeline):
        raise TypeError(
            "The customer risk artifact must contain a sklearn pipeline."
        )
    logger.info("Loaded customer risk model artifact %s", artifact.id)
    return {"model": model, "artifact_id": str(artifact.id)}


@step(enable_cache=False)
def score_customer(
    customer_features: dict[str, float],
) -> Annotated[dict[str, Any], "prediction"]:
    """Estimate the probability of a customer being at risk.

    Args:
        customer_features: Named numeric features describing one customer.

    Returns:
        Probability, risk classification, and the model artifact identifier.

    Raises:
        RuntimeError: If the deployment model has not been initialized.
    """
    state = get_step_context().pipeline_state
    if not isinstance(state, dict) or not isinstance(
        state.get("model"), Pipeline
    ):
        raise RuntimeError("The customer risk model has not been initialized.")
    model = state["model"]
    frame = pd.DataFrame([customer_features])
    probability = float(model.predict_proba(frame)[0, 1])
    result = {
        "risk_probability": round(probability, 6),
        "at_risk": probability >= 0.5,
        "model_artifact_id": state["artifact_id"],
    }
    log_metadata(metadata={"model_artifact_id": state["artifact_id"]})
    return result


@pipeline(
    enable_cache=False,
    on_init=initialize_risk_service,
    settings={
        "docker": DockerSettings(requirements="requirements.txt"),
        "deployment": DeploymentSettings(
            app_title="Customer Risk Service",
            app_description="Estimate customer risk from account information.",
        ),
    },
)
def customer_risk(
    customer_features: dict[str, float] = {
        "monthly_charges": 80.0,
        "account_length": 12.0,
        "support_calls": 3.0,
    },
) -> dict[str, Any]:
    """Serve customer risk predictions.

    Args:
        customer_features: Named numeric customer features.

    Returns:
        The customer prediction and its model artifact identifier.
    """
    return score_customer(customer_features=customer_features)
