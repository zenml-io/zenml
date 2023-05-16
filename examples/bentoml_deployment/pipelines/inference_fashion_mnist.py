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
from zenml.integrations.constants import BENTOML, PYTORCH
from zenml.pipelines import pipeline

docker_settings = DockerSettings(required_integrations=[PYTORCH, BENTOML])


@pipeline(settings={"docker": docker_settings})
def inference_fashion_mnist(
    inference_loader,
    prediction_service_loader,
    predictor,
):
    """Link all the steps and artifacts together."""
    inference_data = inference_loader()
    prediction_service = prediction_service_loader()
    predictor(inference_data=inference_data, service=prediction_service)
