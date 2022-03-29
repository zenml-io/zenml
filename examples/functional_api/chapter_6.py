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
import os

import numpy as np
import pandas as pd
import requests
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression

from zenml.integrations.constants import SKLEARN
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import BaseStepConfig, Output, step

# Path to a pip requirements file that contains requirements necessary to run
# the pipeline
requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")


class ImporterConfig(BaseStepConfig):
    n_days: int = 1


def get_X_y_from_api(n_days: int = 1, is_train: bool = True):
    url = (
        "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_train.json"
        if is_train
        else "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_test.json"
    )
    df = pd.DataFrame(requests.get(url).json())
    X = df["image"].map(lambda x: np.array(x)).values
    X = np.array([x.reshape(28, 28) for x in X])
    y = df["label"].map(lambda y: np.array(y)).values
    return X, y


@step
def dynamic_importer(
    config: ImporterConfig,
) -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Downloads the latest data from a mock API."""
    X_train, y_train = get_X_y_from_api(n_days=config.n_days, is_train=True)
    X_test, y_test = get_X_y_from_api(n_days=config.n_days, is_train=False)
    return X_train, y_train, X_test, y_test


@step
def normalize_mnist(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


@step
def sklearn_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train SVC from sklearn."""
    clf = LogisticRegression(penalty="l1", solver="saga", tol=0.1)
    clf.fit(X_train.reshape((X_train.shape[0], -1)), y_train)
    return clf


@step
def sklearn_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate accuracy score with classifier."""

    test_acc = model.score(X_test.reshape((X_test.shape[0], -1)), y_test)
    return test_acc


@pipeline(
    enable_cache=False,
    required_integrations=[SKLEARN],
    requirements_file=requirements_file,
)
def mnist_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    X_train, y_train, X_test, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)


if __name__ == "__main__":

    # Initialize a new pipeline run
    scikit_p = mnist_pipeline(
        importer=dynamic_importer(),
        normalizer=normalize_mnist(),
        trainer=sklearn_trainer(),
        evaluator=sklearn_evaluator(),
    )

    # Run the new pipeline
    scikit_p.run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="mnist_pipeline")
    print(f"Pipeline `mnist_pipeline` has {len(p.runs)} run(s)")
    eval_step = p.runs[-1].get_step("evaluator")
    val = eval_step.output.read()
    print(f"We scored an accuracy of {val} on the latest run!")
