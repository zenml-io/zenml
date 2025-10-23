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

"""Churn prediction inference pipeline."""

from typing import Any, Dict

from pipelines.hooks import cleanup_model, init_model
from steps import predict_churn

from zenml import pipeline
from zenml.config import DeploymentSettings, DockerSettings
from zenml.config.resource_settings import ResourceSettings


@pipeline(
    enable_cache=False,
    on_init=init_model,
    on_cleanup=cleanup_model,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            parent_image="zenmldocker/zenml:0.84.3-py3.12",
        ),
        "deployment": DeploymentSettings(
            app_title="Customer Churn Prediction Service",
            app_description="Real-time churn prediction with interactive web interface",
            app_version="1.0.0",
            dashboard_files_path="frontend",
        ),
        "deployer": {
            "generate_auth_key": True,
        },
        "resources": ResourceSettings(
            memory="1GB",
            cpu_count=1,
            min_replicas=1,
            max_replicas=3,
            max_concurrency=10,
        ),
    },
)
def churn_inference_pipeline(
    customer_features: Dict[str, float] = {
        "account_length": 100,
        "customer_service_calls": 2,
        "monthly_charges": 50.0,
        "total_charges": 1200.0,
        "has_internet_service": 1,
        "has_phone_service": 1,
        "contract_length": 12,
        "payment_method_electronic": 1,
    },
) -> Dict[str, Any]:
    """Predict customer churn probability for a given customer.

    This pipeline uses a pre-loaded churn prediction model (loaded during
    deployment initialization) to make fast predictions for customers.

    Args:
        customer_features: Dictionary containing customer features:
            - account_length: How long customer has been with company (months)
            - customer_service_calls: Number of customer service calls
            - monthly_charges: Monthly charges ($)
            - total_charges: Total charges to date ($)
            - has_internet_service: 1 if has internet, 0 otherwise
            - has_phone_service: 1 if has phone, 0 otherwise
            - contract_length: Contract length in months (1, 12, or 24)
            - payment_method_electronic: 1 if electronic payment, 0 otherwise

    Returns:
        Dictionary containing:
            - churn_probability: Probability of churn (0.0 to 1.0)
            - churn_prediction: Binary prediction (0 or 1)
            - model_version: Version of the model used (string)
            - model_status: Status of the prediction ("success", "error", etc.)
    """
    prediction: Dict[str, Any] = predict_churn(
        customer_features=customer_features
    )
    return prediction
