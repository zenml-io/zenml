#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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


import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.integrations.slack.steps.slack_alerter_step import slack_alerter_step
from zenml.pipelines import pipeline
from zenml.steps import Output, step


@step
def importer() -> Output(
    X_train=np.ndarray,
    X_test=np.ndarray,
    y_train=np.ndarray,
    y_test=np.ndarray,
):
    """Load the digits dataset as numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate the test set accuracy of an sklearn model."""
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return test_acc


@step
def test_acc_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return f"Test Accuracy: {test_acc}"


@pipeline
def slack_pipeline(importer, trainer, evaluator, formatter, alertor):
    """Train and evaluate a model and post the test accuracy to slack."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = formatter(test_acc)
    alertor(message)


if __name__ == "__main__":
    slack_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        formatter=test_acc_formatter(),
        alertor=slack_alerter_step(),
    ).run()
