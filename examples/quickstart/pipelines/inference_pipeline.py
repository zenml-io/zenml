#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from steps import (
    drift_detector,
    inference_data_loader,
    predictor,
    training_data_loader,
)

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import SKLEARN
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)

docker_settings = DockerSettings(
    required_integrations=[SKLEARN],
)


model_deployer = mlflow_model_registry_deployer_step.with_options(
    parameters=dict(
        registry_model_name="zenml-quickstart-model",
        registry_model_version="1",
        # or you can use the model stage if you have set it in the MLflow registry
        # registered_model_stage="None" # "Staging", "Production", "Archived"
    )
)


@pipeline(settings={"docker": docker_settings})
def inference_pipeline():
    """Inference pipeline with skew and drift detection."""
    inference_data = inference_data_loader()
    model_deployment_service = model_deployer()
    predictor(service=model_deployment_service, data=inference_data)
    training_data, _, _, _ = training_data_loader()
    drift_detector(training_data, inference_data)
