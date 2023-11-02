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


from steps.common.importer import importer
from steps.common.normalizer import normalizer
from steps.pytorch.data_loader import pytorch_data_loader
from steps.pytorch.evaluator import pytorch_evaluator
from steps.pytorch.trainer import pytorch_trainer
from steps.sklearn.evaluator import sklearn_evaluator
from steps.sklearn.trainer import sklearn_trainer
from steps.tensorflow.evaluator import tf_evaluator
from steps.tensorflow.trainer import tf_trainer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import PYTORCH, SELDON, SKLEARN, TENSORFLOW
from zenml.integrations.seldon.seldon_client import SeldonResourceRequirements
from zenml.integrations.seldon.services import (
    SeldonDeploymentConfig,
)
from zenml.integrations.seldon.steps import (
    seldon_model_deployer_step,
)
from zenml.integrations.seldon.steps.seldon_deployer import (
    seldon_custom_model_deployer_step,
)

docker_settings = DockerSettings(
    requirements=["torchvision", "Pillow"],
    required_integrations=[SELDON, TENSORFLOW, SKLEARN, PYTORCH],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def seldon_deployment_pipeline(
    custom_code: bool = False,
    model_name: str = "mnist",
    model_flavor: str = "sklearn",
    epochs: int = 5,
    lr: float = 0.003,
    solver: str = "saga",
    penalty: str = "l1",
    penalty_strength: float = 1.0,
    toleration: float = 0.1,
    timeout: int = 240,
):
    # Pytorch load, train, and evaluate
    if model_flavor == "pytorch":
        train_loader, test_loader = pytorch_data_loader()
        model = pytorch_trainer(train_loader)
        pytorch_evaluator(model=model, test_loader=test_loader)

    # Sklearn & TensorFlow load, train, and evaluate
    else:
        x_train, y_train, x_test, y_test = importer()
        if not custom_code:
            x_train, x_test = normalizer(x_train=x_train, x_test=x_test)
        if model_flavor == "tensorflow":
            model = tf_trainer(
                x_train=x_train, y_train=y_train, epochs=epochs, lr=lr
            )
            tf_evaluator(x_test=x_test, y_test=y_test, model=model)
        else:
            model = sklearn_trainer(
                x_train=x_train,
                y_train=y_train,
                solver=solver,
                penalty=penalty,
                C=penalty_strength,
                tol=toleration,
            )
            sklearn_evaluator(x_test=x_test, y_test=y_test, model=model)

    # Seldon deployment config
    if custom_code:
        seldon_implementation = "custom"
    elif model_flavor == "tensorflow":
        seldon_implementation = "TENSORFLOW_SERVER"
    elif model_flavor == "pytorch":
        seldon_implementation = "TORCH_SERVER"
    else:
        seldon_implementation = "SKLEARN_SERVER"
    service_config = SeldonDeploymentConfig(
        model_name=model_name,
        replicas=1,
        implementation=seldon_implementation,
        resources=SeldonResourceRequirements(
            limits={"cpu": "200m", "memory": "250Mi"}
        ),
    )

    # Custom code deployment step
    if custom_code:
        if model_flavor == "tensorflow":
            predict_function = "custom_predict.tensorflow.custom_predict"
        else:
            predict_function = "custom_predict.pytorch.custom_predict"
        seldon_custom_model_deployer_step(
            model=model,
            predict_function=predict_function,
            service_config=service_config,
            timeout=timeout,
        )

    # Deployment step
    else:
        seldon_model_deployer_step(
            model=model,
            service_config=service_config,
            timeout=timeout,
        )
