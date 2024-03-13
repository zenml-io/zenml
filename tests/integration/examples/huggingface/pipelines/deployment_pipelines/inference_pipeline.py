#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


from steps.prediction_service_loader.prediction_service_loader import (
    prediction_service_loader,
)
from steps.predictor.predictor import predictor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import HUGGINGFACE

docker_settings = DockerSettings(
    required_integrations=[HUGGINGFACE],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def inference_pipeline(
    deployment_pipeline_name: str = "huggingface_deployment_pipeline",
    model_name: str = "hf",
    deployer_step_name: str = "huggingface_model_deployer_step",
):
    inference_data = "Test text"
    model_deployment_service = prediction_service_loader(
        pipeline_name=deployment_pipeline_name,
        step_name=deployer_step_name,
        model_name=model_name,
    )

    # Run the predictor
    predictor(model_deployment_service, inference_data)
