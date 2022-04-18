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

import logging
import os
from typing import cast

import joblib
import numpy as np  # type: ignore [import]
import pandas as pd
import requests  # type: ignore [import]
import seldon_core
import tensorflow as tf  # type: ignore [import]
from rich import print
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression

from zenml.integrations.constants import SELDON, SKLEARN, TENSORFLOW
from zenml.integrations.seldon.custom_deployer.ZenMLCustomModel import (
    ZenMLCustomModel,
)
from zenml.integrations.seldon.model_deployers import SeldonModelDeployer
from zenml.integrations.seldon.services import SeldonDeploymentService
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step

logger = get_logger(__name__)


@step
def importer_mnist() -> Output(
    x_train=np.ndarray, y_train=np.ndarray, x_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (x_train, y_train), (
        x_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return x_train, y_train, x_test, y_test


@step
def normalizer(
    x_train: np.ndarray, x_test: np.ndarray
) -> Output(x_train_normed=np.ndarray, x_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    x_train_normed = x_train / 255.0
    x_test_normed = x_test / 255.0
    return x_train_normed, x_test_normed


class TensorflowTrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 1
    lr: float = 0.001


@step
def tf_trainer(
    config: TensorflowTrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(config.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        x_train,
        y_train,
        epochs=config.epochs,
    )

    # write model
    return model


@step
def tf_evaluator(
    x_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""

    _, test_acc = model.evaluate(x_test, y_test, verbose=2)
    return test_acc


class SklearnTrainerConfig(BaseStepConfig):
    """Trainer params"""

    solver: str = "saga"
    penalty: str = "l1"
    C: float = 1.0
    tol: float = 0.1


@step
def sklearn_trainer(
    config: SklearnTrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train SVC from sklearn."""
    clf = LogisticRegression(
        penalty=config.penalty, solver=config.solver, tol=config.tol, C=config.C
    )
    clf.fit(x_train.reshape((x_train.shape[0], -1)), y_train)
    return clf


@step
def sklearn_evaluator(
    x_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate accuracy score with classifier."""

    test_acc = model.score(x_test.reshape((x_test.shape[0], -1)), y_test)
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


class CustomModelParameters(BaseStepConfig):
    """Parameters that are used to trigger the deployment"""

    model_class: str = None


# TODO [HIGH]: This should be a automated way to get the class name rather than hardcoding it
@step
def custom_class_source_retrive(
    config: CustomModelParameters,
) -> str:
    """Step that retrieves the source path of the custom model class"""
    if config.model_class:
        return config.model_class
    else:
        return ""


class SeldonDeploymentLoaderStepConfig(BaseStepConfig):
    """Seldon deployment loader configuration

    Attributes:
        pipeline_name: name of the pipeline that deployed the Seldon prediction
            server
        step_name: the name of the step that deployed the Seldon prediction
            server
        model_name: the name of the model that was deployed
    """

    pipeline_name: str
    step_name: str
    model_name: str


@step(enable_cache=False)
def prediction_service_loader(
    config: SeldonDeploymentLoaderStepConfig,
) -> SeldonDeploymentService:
    """Get the prediction service started by the deployment pipeline"""

    model_deployer = SeldonModelDeployer.get_active_model_deployer()

    services = model_deployer.find_model_server(
        pipeline_name=config.pipeline_name,
        pipeline_step_name=config.step_name,
        model_name=config.model_name,
    )
    if not services:
        raise RuntimeError(
            f"No Seldon Core prediction server deployed by the "
            f"'{config.step_name}' step in the '{config.pipeline_name}' "
            f"pipeline for the '{config.model_name}' model is currently "
            f"running."
        )

    if not services[0].is_running:
        raise RuntimeError(
            f"The Seldon Core prediction server last deployed by the "
            f"'{config.step_name}' step in the '{config.pipeline_name}' "
            f"pipeline for the '{config.model_name}' model is not currently "
            f"running."
        )

    return cast(SeldonDeploymentService, services[0])


def get_data_from_api():
    url = (
        "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_test.json"
    )

    df = pd.DataFrame(requests.get(url).json())
    data = df["image"].map(lambda x: np.array(x)).values
    data = np.array([x.reshape(28, 28) for x in data])
    return data


@step(enable_cache=False)
def dynamic_importer() -> Output(data=np.ndarray):
    """Downloads the latest data from a mock API."""
    data = get_data_from_api()
    return data


@step
def tf_predict_preprocessor(input: np.ndarray) -> Output(data=np.ndarray):
    """Prepares the data for inference."""
    input = input / 255.0
    return input


@step
def sklearn_predict_preprocessor(input: np.ndarray) -> Output(data=np.ndarray):
    """Prepares the data for inference."""
    input = input / 255.0
    return input.reshape((input.shape[0], -1))


@step
def predictor(
    service: SeldonDeploymentService,
    data: np.ndarray,
) -> Output(predictions=np.ndarray):
    """Run a inference request against a prediction service"""

    service.start(timeout=120)  # should be a NOP if already started
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)
    print("Prediction: ", prediction)
    return prediction


@pipeline(
    enable_cache=True, required_integrations=[SELDON, TENSORFLOW, SKLEARN]
)
def continuous_deployment_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
    deployment_trigger,
    custom_class_source_retrive,
    custom_model_deployer,
):
    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer()
    x_trained_normed, x_test_normed = normalizer(x_train=x_train, x_test=x_test)
    model = trainer(x_train=x_trained_normed, y_train=y_train)
    accuracy = evaluator(x_test=x_test_normed, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(accuracy=accuracy)
    source = custom_class_source_retrive()
    custom_model_deployer(
        deployment_decision,
        model,
        custom_class_path=source,
    )


@pipeline(
    enable_cache=True, required_integrations=[SELDON, TENSORFLOW, SKLEARN]
)
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


class mycustomdeploy(ZenMLCustomModel):
    """Custom model deployment class"""

    def __init__(self, model_uri: str = None):
        super().__init__(model_uri=model_uri)

    def load(self):
        """Load the model from the given path"""
        try:
            model_file = os.path.join(
                seldon_core.Storage.download(self.model_uri), "model.joblib"
            )
            self.model = joblib.load(model_file)
            self.ready = True
        except Exception as ex:
            logging.exception("Exception during predict", ex)
            self.ready = False

    def predict(self, X, features_names):
        """Run a prediction on the given data"""
        try:
            logger.info("Calling predict_proba")
            result = self.model.predict_proba(X)
            return result
        except Exception as ex:
            logging.exception("Exception during predict", ex)
            raise
