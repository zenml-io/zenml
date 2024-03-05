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

from steps.inference_loader import inference_loader
from steps.prediction_service_loader import bentoml_prediction_service_loader
from steps.predictor import predictor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import BENTOML, PYTORCH

docker_settings = DockerSettings(required_integrations=[PYTORCH, BENTOML])


@pipeline(settings={"docker": docker_settings})
def inference_fashion_mnist(
    model_name: str, pipeline_name: str, step_name: str
):
    """Perform inference with a model deployed through BentoML.

    Args:
        pipeline_name: The name of the pipeline that deployed the model.
        step_name: The name of the step that deployed the model.
        model_name: The name of the model that was deployed.
    """
    inference_data = inference_loader()
    prediction_service = bentoml_prediction_service_loader(
        model_name=model_name, pipeline_name=pipeline_name, step_name=step_name
    )
    predictor(inference_data=inference_data, service=prediction_service)
