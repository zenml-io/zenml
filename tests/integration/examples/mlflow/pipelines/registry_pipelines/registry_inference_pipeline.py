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
from steps.predictor_step import predictor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)

docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN], requirements=["scikit-image"]
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def mlflow_registry_inference_pipeline():
    # Link all the steps artifacts together
    deployed_model = mlflow_model_registry_deployer_step(
        registry_model_name="sklearn-mnist-model",
        registry_model_version="1",
        # or you can use the model stage if you have set it in the MLflow registry
        # registered_model_stage="None" # "Staging", "Production", "Archived"
    )
    batch_data = dynamic_importer()
    inference_data = predict_preprocessor(batch_data)
    predictor(deployed_model, inference_data)
