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
from steps.params import TrainerConfig
from steps.sklearn_trainer import sklearn_evaluator, sklearn_trainer
from steps.tf_steps import tf_evaluator, tf_trainer
from steps.torch_steps import torch_evaluator, torch_trainer

from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def normalizer(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


# Define the pipeline
@pipeline
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


# Initialize a pipeline run
tf_p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=tf_trainer(config=TrainerConfig(epochs=1)),
    evaluator=tf_evaluator(),
)

# Run the pipeline
tf_p.run()

# Initialize a new pipeline run
torch_p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=torch_trainer(config=TrainerConfig(epochs=1)),
    evaluator=torch_evaluator(),
)

# Run the new pipeline
torch_p.run()

# Initialize a new pipeline run
scikit_p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=sklearn_trainer(config=TrainerConfig()),
    evaluator=sklearn_evaluator(),
)

# Run the new pipeline
scikit_p.run()

# Post-execution flow
repo = Repository()
pipeline = repo.get_pipelines()[0]
print("***********************OUTPUT************************")
for r in pipeline.runs[-3:]:
    eval_step = r.get_step("evaluator")
    print(
        f"For {eval_step.entrypoint_name}, the accuracy is: "
        f"{eval_step.output.read():.2f}"
    )
