#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import click
import numpy as np
from sklearn.base import ClassifierMixin

from zenml.integrations.constants import SELDON, SKLEARN
from zenml.integrations.kserve.services import KServeDeploymentConfig
from zenml.integrations.kserve.steps import (
    KServeDeployerStepConfig,
    kserve_model_deployer_step,
)
from zenml.integrations.sklearn.helpers.digits import (
    get_digits,
    get_digits_model,
)
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step


@step
def importer() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits array as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a simple sklearn classifier for the digits dataset."""
    model = get_digits_model()
    model.fit(X_train, y_train)
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return test_acc


class DeploymentTriggerConfig(BaseStepConfig):
    """Parameters that are used to trigger the deployment"""

    min_accuracy: float


@step
def deployment_trigger(
    accuracy: float,
    config: DeploymentTriggerConfig,
) -> bool:
    """Implements a simple model deployment trigger that looks at the
    input model accuracy and decides if it is good enough to deploy"""

    return accuracy > config.min_accuracy


@pipeline(required_integrations=[SKLEARN])
def mnist_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)


@pipeline(required_integrations=[SKLEARN, SELDON])
def deploy_mnist_pipeline(
    importer,
    trainer,
    evaluator,
    deployment_trigger,
    model_deployer,
):
    """Links all the steps together in a pipeline"""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    accuracy = evaluator(X_test=X_test, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(accuracy=accuracy)
    model_deployer(deployment_decision, model)


DEPLOY = "deploy"


@click.command()
@click.option("--deploy", "-d", is_flag=False, help="Deploy the model")
@click.option("--lr", default=0.001, help="Learning rate for training")
@click.option(
    "--min-accuracy",
    default=0.85,
    help="Minimum accuracy required to deploy the model (default: 0.92)",
)
def main(
    deploy: str,
    lr: float,
    min_accuracy: float,
):
    """Run the mnist example pipeline"""

    model_name = "mnist"
    kserve_predictor = "sklearn"
    if deploy:
        deployment_pipeline = deploy_mnist_pipeline(
            importer=importer(),
            trainer=trainer(),
            evaluator=evaluator(),
            deployment_trigger=deployment_trigger(
                config=DeploymentTriggerConfig(
                    min_accuracy=min_accuracy,
                )
            ),
            model_deployer=kserve_model_deployer_step(
                config=KServeDeployerStepConfig(
                    service_config=KServeDeploymentConfig(
                        model_name=model_name,
                        replicas=1,
                        predictor=kserve_predictor,
                        resources={"requests": {"cpu": "100m","memory": "100m"}},
                    ),
                    timeout=120,
                )
            ),
        )
        deployment_pipeline.run()

    else:
        # Run the pipeline
        pipeline = mnist_pipeline(
            importer=importer(),
            trainer=trainer(),
            evaluator=evaluator(),
        )
        pipeline.run()


if __name__ == "__main__":
    main()
