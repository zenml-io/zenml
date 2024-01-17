# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
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

from typing import Optional

import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier
from typing_extensions import Annotated

from zenml import ArtifactConfig, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def model_trainer(
    dataset_trn: pd.DataFrame,
    model_type: str = "sgd",
    target: Optional[str] = "target",
) -> Annotated[
    ClassifierMixin,
    ArtifactConfig(name="sklearn_classifier", is_model_artifact=True),
]:
    """Configure and train a model on the training dataset.

    This is an example of a model training step that takes in a dataset artifact
    previously loaded and pre-processed by other steps in your pipeline, then
    configures and trains a model on it. The model is then returned as a step
    output artifact.

    Args:
        dataset_trn: The preprocessed train dataset.
        model_type: The type of model to train.
        target: The name of the target column in the dataset.

    Returns:
        The trained model artifact.

    Raises:
        ValueError: If the model type is not supported.
    """
    # Initialize the model with the hyperparameters indicated in the step
    # parameters and train it on the training set.
    if model_type == "sgd":
        model = SGDClassifier()
    elif model_type == "rf":
        model = RandomForestClassifier()
    else:
        raise ValueError(f"Unknown model type {model_type}")
    logger.info(f"Training model {model}...")

    model.fit(
        dataset_trn.drop(columns=[target]),
        dataset_trn[target],
    )
    return model
