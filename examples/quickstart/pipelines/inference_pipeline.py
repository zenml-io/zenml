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

from zenml.config import DockerSettings
from zenml.integrations.constants import SKLEARN
from zenml.pipelines import pipeline

docker_settings = DockerSettings(
    required_integrations=[SKLEARN],
)


@pipeline(settings={"docker": docker_settings})
def inference_pipeline(
    inference_data_loader,
    mlflow_model_deployer,
    predictor,
    training_data_loader,
    drift_detector,
):
    """Inference pipeline with skew and drift detection."""
    inference_data = inference_data_loader()
    model_deployment_service = mlflow_model_deployer()
    predictor(model_deployment_service, inference_data)
    training_data, _, _, _ = training_data_loader()
    drift_detector(training_data, inference_data)
