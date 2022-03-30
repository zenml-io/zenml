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
import tensorflow as tf

from zenml.integrations.constants import TENSORFLOW
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data and store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def normalize_mnist(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


@pipeline(required_integrations=[TENSORFLOW])
def load_and_normalize_pipeline(
    importer,
    normalizer,
):
    """Pipeline now has two steps we need to connect together"""
    X_train, y_train, X_test, y_test = importer()
    normalizer(X_train=X_train, X_test=X_test)


if __name__ == "__main__":

    # Run the pipeline
    load_and_normalize_pipeline(
        importer=importer_mnist(), normalizer=normalize_mnist()
    ).run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="load_and_normalize_pipeline")
    runs = p.runs
    print(f"Pipeline `load_and_normalize_pipeline` has {len(runs)} run(s)")
    run = runs[-1]
    print(f"The run you just made has {len(run.steps)} steps.")
    step = run.get_step("normalizer")
    print(f"The `normalizer` step has {len(step.outputs)} output artifacts.")
    for k, o in step.outputs.items():
        arr = o.read()
        print(f"Output '{k}' is an array with shape: {arr.shape}")
