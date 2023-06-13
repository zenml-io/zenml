#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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


from steps.common.deployment_trigger import deployment_trigger
from steps.common.importer import importer_mnist
from steps.common.normalizer import normalizer
from steps.sklearn.evaluator import sklearn_evaluator
from steps.sklearn.trainer import sklearn_trainer
from steps.tensorflow.evaluator import tf_evaluator
from steps.tensorflow.trainer import tf_trainer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import SELDON, SKLEARN, TENSORFLOW
from zenml.integrations.seldon.seldon_client import SeldonResourceRequirements
from zenml.integrations.seldon.services import (
    SeldonDeploymentConfig,
)
from zenml.integrations.seldon.steps import (
    seldon_model_deployer_step,
)

docker_settings = DockerSettings(
    required_integrations=[SELDON, TENSORFLOW, SKLEARN]
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def continuous_deployment_pipeline(
    model_name: str,
    model_flavor: str = "sklearn",
    epochs: int = 5,
    lr: float = 0.003,
    solver: str = "saga",
    penalty: str = "l1",
    penalty_strength: float = 1.0,
    toleration: float = 0.1,
    min_accuracy: float = 0.9,
):
    # Configure model deployer
    if model_flavor == "tensorflow":
        seldon_implementation = "TENSORFLOW_SERVER"
    else:
        seldon_implementation = "SKLEARN_SERVER"

    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer_mnist()
    x_trained_normed, x_test_normed = normalizer(
        x_train=x_train, x_test=x_test
    )
    if model_flavor == "tensorflow":
        model = tf_trainer(
            x_train=x_trained_normed, y_train=y_train, epochs=epochs, lr=lr
        )
        accuracy = tf_evaluator(
            x_test=x_test_normed, y_test=y_test, model=model
        )
    else:
        model = sklearn_trainer(
            x_train=x_trained_normed,
            y_train=y_train,
            solver=solver,
            penalty=penalty,
            C=penalty_strength,
            tol=toleration,
        )
        accuracy = sklearn_evaluator(
            x_test=x_test_normed, y_test=y_test, model=model
        )
    deployment_decision = deployment_trigger(
        accuracy=accuracy, min_accuracy=min_accuracy
    )
    seldon_model_deployer_step(
        model=model,
        deploy_decision=deployment_decision,
        service_config=SeldonDeploymentConfig(
            model_name=model_name,
            replicas=1,
            implementation=seldon_implementation,
            resources=SeldonResourceRequirements(
                limits={"cpu": "200m", "memory": "250Mi"}
            ),
        ),
        timeout=120,
    )
