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
from steps.deployment_trigger.deployment_trigger_step import (
    deployment_trigger,
)
from steps.importer.importer_step import importer_mnist
from steps.normalizer.normalizer_step import normalizer
from steps.prediction_service_loader.prediction_service_loader_step import (
    model_deployer,
)
from steps.tf_evaluator.tf_evaluator_step import tf_evaluator
from steps.tf_trainer.tf_trainer_step import tf_trainer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.constants import MLFLOW, TENSORFLOW

docker_settings = DockerSettings(required_integrations=[MLFLOW, TENSORFLOW])


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def continuous_deployment_pipeline(
    epochs: int = 1,
    lr: float = 0.001,
    min_accuracy: float = 0.9,
    workers: int = 1,
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
):
    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer_mnist()
    x_trained_normed, x_test_normed = normalizer(
        x_train=x_train, x_test=x_test
    )
    model = tf_trainer(
        x_train=x_trained_normed, y_train=y_train, lr=lr, epochs=epochs
    )
    accuracy = tf_evaluator(x_test=x_test_normed, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(
        accuracy=accuracy, min_accuracy=min_accuracy
    )
    model_deployer(
        model=model,
        deploy_decision=deployment_decision,
        workers=workers,
        timeout=timeout,
    )
