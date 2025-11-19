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

"""Training step for churn prediction model."""

from typing import Annotated, Tuple

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from zenml import ArtifactConfig, add_tags, log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_churn_model(
    features: pd.DataFrame,
    target: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[
    Annotated[
        Pipeline, ArtifactConfig(name="churn-model", tags=["production"])
    ],
    Annotated[float, "accuracy"],
]:
    """Train a churn prediction model and return model with accuracy.

    Args:
        features: Customer features DataFrame
        target: Churn target variable
        test_size: Proportion of data to use for testing
        random_state: Random seed for reproducibility

    Returns:
        Tuple of trained model pipeline and accuracy score
    """
    logger.info(f"Training churn model on {len(features)} samples...")

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=target,
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=random_state,
                    class_weight="balanced",  # Handle class imbalance
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc_score = roc_auc_score(y_test, y_pred_proba)

    logger.info("Model trained successfully!")
    logger.info(f"Accuracy: {accuracy:.3f}")
    logger.info(f"AUC Score: {auc_score:.3f}")
    logger.info("Classification Report:")
    logger.info(f"\n{classification_report(y_test, y_pred, zero_division=0)}")

    log_metadata(
        metadata={
            "training": {
                "accuracy": round(accuracy, 3),
                "auc_score": round(auc_score, 3),
                "samples": len(features),
                "features": len(features.columns),
            }
        },
        artifact_name="churn-model",
        infer_artifact=True,
    )

    add_tags(
        tags=["production"], artifact_name="churn-model", infer_artifact=True
    )
    logger.info("Tagged model as 'production'")

    return pipeline, accuracy
