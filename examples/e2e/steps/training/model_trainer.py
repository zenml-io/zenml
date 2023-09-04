# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import mlflow
import pandas as pd
from artifacts.model_metadata import ModelMetadata
from sklearn.base import ClassifierMixin
from typing_extensions import Annotated

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

experiment_tracker = Client().active_stack.experiment_tracker

if not experiment_tracker or not isinstance(
    experiment_tracker, MLFlowExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain a MLFlow experiment tracker for "
        "this example to work."
    )


@step(experiment_tracker=experiment_tracker.name)
def model_trainer(
    dataset_trn: pd.DataFrame,
    model_config: ModelMetadata,
    target: str,
    random_seed: int = 42,
) -> Annotated[ClassifierMixin, "model"]:
    """Configure and train a model on the training dataset.

    This is an example of a model training step that takes in a dataset artifact
    previously loaded and pre-processed by other steps in your pipeline, then
    configures and trains a model on it. The model is then returned as a step
    output artifact.

    Model training steps should have caching disabled if they are not
    deterministic (i.e. if the model training involve some random processes
    like initializing weights or shuffling data that are not controlled by
    setting a fixed random seed). This example step ensures the outcome is
    deterministic by initializing the model with a fixed random seed.

    This step is parameterized to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use a different model, change the random seed, or pass different
    hyperparameters to the model constructor. See the documentation for more
    information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        dataset_trn: The preprocessed train dataset.
        model_config: `ModelMetadata` to train on
        target: Name of target columns in dataset.
        random_seed: Fixed seed of random generator.

    Returns:
        The trained model artifact.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Initialize the model with the hyperparameters indicated in the step
    # parameters and train it on the training set.
    hyperparameters = model_config.params
    model_class = model_config.model_class
    if "random_seed" in model_class.__init__.__code__.co_varnames:
        model = model_class(random_seed=random_seed, **hyperparameters)
    else:
        model = model_class(**hyperparameters)

    logger.info(f"Training model {model}...")
    mlflow.sklearn.autolog()
    model.fit(
        dataset_trn.drop(columns=[target]),
        dataset_trn[target],
    )
    ### YOUR CODE ENDS HERE ###

    return model
