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
import numpy as np
from sklearn.base import ClassifierMixin

from zenml.integrations.constants import S3, SKLEARN
from zenml.integrations.sklearn.helpers.digits import (
    get_digits,
    get_digits_model,
)
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step

step_operator = Repository().active_stack.step_operator
if not step_operator:
    raise RuntimeError(
        "Your active stack needs to contain a step operator for this example "
        "to work."
    )


@step
def importer() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits array as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


# setting the custom_step_operator param will tell ZenML
# to run this step on a custom backend defined by the name
# of the operator you provide.
@step(custom_step_operator=step_operator.name)
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


@pipeline(required_integrations=[SKLEARN, S3])
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
        evaluator=evaluator(),
    )
    pipeline.run()
