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

"""Inference step for churn prediction."""

from typing import Annotated, Dict

import pandas as pd
from sklearn.pipeline import Pipeline

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def predict_churn(
    customer_features: Dict[str, float], model_name: str = "churn-model"
) -> Annotated[Dict[str, float], "prediction"]:
    """Predict churn probability for a customer.

    Args:
        customer_features: Dictionary of customer features
        model_name: Name of the model artifact to load

    Returns:
        Dictionary containing churn probability and prediction
    """
    logger.info(
        f"Making churn prediction for customer features: {customer_features}"
    )

    # Load the production model
    client = Client()
    try:
        # Get the latest version of the model (it should be tagged as production)
        model_artifact = client.get_artifact_version(
            name_id_or_prefix=model_name
        )
        model: Pipeline = model_artifact.load()
        logger.info(f"Loaded model version: {model_artifact.version}")
    except Exception as e:
        logger.error(f"Failed to load model '{model_name}': {e}")
        # Return a default prediction if model loading fails
        return {
            "churn_probability": 0.5,
            "churn_prediction": 1,
            "model_status": "error",
            "error": str(e),
        }

    try:
        # Convert features to DataFrame (model expects this format)
        features_df = pd.DataFrame([customer_features])

        # Make prediction
        churn_probability = float(model.predict_proba(features_df)[0, 1])
        churn_prediction = int(churn_probability > 0.5)

        result = {
            "churn_probability": round(churn_probability, 3),
            "churn_prediction": churn_prediction,
            "model_version": model_artifact.version,
            "model_status": "success",
        }

        logger.info(f"Prediction result: {result}")
        return result

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            "churn_probability": 0.5,
            "churn_prediction": 1,
            "model_status": "prediction_error",
            "error": str(e),
        }
