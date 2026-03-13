#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Train step: read validated data from LakeFS, train a scikit-learn model."""

from typing import Annotated, Dict, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from utils import LakeFSRef
from utils.lakefs_utils import read_parquet_from_lakefs

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_model(
    validated_ref: LakeFSRef,
) -> Tuple[
    Annotated[RandomForestRegressor, "trained_model"],
    Annotated[Dict[str, float], "training_metrics"],
]:
    """Train a RandomForestRegressor on validated sensor data from LakeFS.

    Predicts temperature from humidity, pressure, and sensor ID. The
    model and metrics are stored in ZenML's artifact store while the
    training data stays in LakeFS — only the small LakeFSRef pointer
    traveled through the pipeline.

    Args:
        validated_ref: Reference to validated data in LakeFS.

    Returns:
        The trained model and a metrics dictionary.
    """
    logger.info(
        "Reading validated data from LakeFS: repo=%s ref=%s path=%s",
        validated_ref.repo,
        validated_ref.ref[:12],
        validated_ref.path,
    )
    df = read_parquet_from_lakefs(
        validated_ref.repo, validated_ref.ref, validated_ref.path
    )

    # Feature engineering
    df = df.copy()
    df["sensor_id_encoded"] = df["sensor_id"].astype("category").cat.codes

    features = ["sensor_id_encoded", "humidity", "pressure"]
    target = "temperature"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    logger.info("Training RandomForestRegressor on %d samples", len(X_train))
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics: Dict[str, float] = {
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "r2": float(r2_score(y_test, y_pred)),
        "n_train": float(len(X_train)),
        "n_test": float(len(X_test)),
    }
    logger.info("Training metrics: %s", metrics)
    log_metadata(metrics)

    return model, metrics
