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


@pipeline(required_integrations=[TENSORFLOW])
def load_mnist_pipeline(
    importer,
):
    """The simplest possible pipeline"""
    # We just need to call the function
    importer()


if __name__ == "__main__":
    # Run the pipeline
    load_mnist_pipeline(importer=importer_mnist()).run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="load_mnist_pipeline")
    runs = p.runs
    print(f"Pipeline `load_mnist_pipeline` has {len(runs)} run(s)")
    run = runs[-1]
    print(f"The run you just made has {len(run.steps)} step(s).")
    step = run.get_step("importer")
    print(f"That step has {len(step.outputs)} output artifacts.")
    for k, o in step.outputs.items():
        arr = o.read()
        print(f"Output '{k}' is an array with shape: {arr.shape}")
