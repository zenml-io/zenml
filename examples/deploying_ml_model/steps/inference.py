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

from zenml import get_step_context, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def predict_churn(
    customer_features: Dict[str, float], model_name: str = "churn-model"
) -> Annotated[Dict[str, float], "prediction"]:
    """Predict churn probability for a customer using pre-loaded model.

    This step uses the model that was loaded during deployment initialization,
    avoiding the overhead of loading the model for each inference request.

    Args:
        customer_features: Dictionary of customer features
        model_name: Name of the model (used for compatibility, actual model comes from pipeline state)

    Returns:
        Dictionary containing churn probability and prediction
    """
    logger.info(
        f"Making churn prediction for customer features: {customer_features}"
    )

    try:
        # Get the pre-loaded model from pipeline state
        step_context = get_step_context()
        model_state = step_context.pipeline_state

        if model_state is None:
            raise RuntimeError(
                "Model not found in pipeline state. Ensure deployment initialization hook is configured."
            )

        # Convert features to DataFrame (model expects this format)
        features_df = pd.DataFrame([customer_features])

        # Make prediction using the pre-loaded model
        churn_probability = float(
            model_state.model.predict_proba(features_df)[0, 1]
        )
        churn_prediction = int(churn_probability > 0.5)

        result = {
            "churn_probability": round(churn_probability, 3),
            "churn_prediction": churn_prediction,
            "model_version": model_state.model_version,
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
