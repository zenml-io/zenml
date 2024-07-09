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
from steps.dynamic_importer_step import dynamic_importer
from steps.predict_preprocessor_step import predict_preprocessor
from steps.prediction_service_loader_step import prediction_service_loader
from steps.predictor_step import predictor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN

docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN], requirements=["scikit-image"]
)


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def mlflow_deployment_inference_pipeline(
    pipeline_name: str = "mlflow_train_deploy_pipeline",
    pipeline_step_name: str = "mlflow_model_deployer_step",
):
    # Link all the steps artifacts together
    batch_data = dynamic_importer()
    inference_data = predict_preprocessor(batch_data)
    model_deployment_service = prediction_service_loader(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
    )
    predictor(model_deployment_service, inference_data)
