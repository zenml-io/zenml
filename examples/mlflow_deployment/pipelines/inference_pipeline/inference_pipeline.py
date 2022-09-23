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
from zenml.integrations.constants import MLFLOW, TENSORFLOW
from zenml.pipelines import pipeline

docker_settings = DockerSettings(required_integrations=[MLFLOW, TENSORFLOW])


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def inference_pipeline(
    dynamic_importer,
    predict_preprocessor,
    prediction_service_loader,
    predictor,
):
    # Link all the steps artifacts together
    batch_data = dynamic_importer()
    inference_data = predict_preprocessor(batch_data)
    model_deployment_service = prediction_service_loader()
    predictor(model_deployment_service, inference_data)
