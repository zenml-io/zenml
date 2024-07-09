#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
from pipelines.tracking_pipeline.tracking_pipeline import (
    mlflow_tracking_pipeline,
)

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN
from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)

docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN], requirements=["scikit-image"]
)


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def mlflow_registry_training_pipeline(
    num_run: int = 1,
):
    model = mlflow_tracking_pipeline()
    mlflow_register_model_step(
        model=model,
        name="sklearn-mnist-model",
        description=(
            f"Run #{num_run} of the mlflow_registry_training_pipeline."
        ),
    )
