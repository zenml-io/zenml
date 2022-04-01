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

import numpy as np
from sklearn.base import ClassifierMixin

from zenml.integrations.constants import SKLEARN
from zenml.integrations.sklearn.helpers.digits import (
    get_digits,
    get_digits_model,
)
from zenml.pipelines import pipeline
from zenml.steps import Output, StepContext, step


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
def evaluate_and_store_best_model(
    context: StepContext,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> ClassifierMixin:
    """Evaluate all models and return the best one."""
    best_accuracy = model.score(X_test, y_test)
    best_model = model

    pipeline_runs = context.metadata_store.get_pipeline("mnist_pipeline").runs
    for run in pipeline_runs:
        # get the trained model of all pipeline runs
        model = run.get_step("trainer").output.read()
        accuracy = model.score(X_test, y_test)
        if accuracy > best_accuracy:
            # if the model accuracy is better than our currently best model,
            # store it
            best_accuracy = accuracy
            best_model = model

    print(f"Best test accuracy: {best_accuracy}")
    return best_model


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


if __name__ == "__main__":

    pipeline = mnist_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluate_and_store_best_model(),
    )
    pipeline.run()
