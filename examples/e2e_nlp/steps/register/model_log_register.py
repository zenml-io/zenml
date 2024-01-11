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

import mlflow
from transformers import (
    PreTrainedModel,
    PreTrainedTokenizerBase,
)

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get experiment tracker
experiment_tracker = Client().active_stack.experiment_tracker

# Check if experiment tracker is set and is of type MLFlowExperimentTracker
if not experiment_tracker or not isinstance(
    experiment_tracker, MLFlowExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain an MLFlow experiment tracker for "
        "this example to work."
    )


@step(experiment_tracker=experiment_tracker.name)
def register_model(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    mlflow_model_name: Optional[str] = "sentiment_analysis",
):
    """
    Register model to MLFlow.

    This step takes in a model and tokenizer artifact previously loaded and pre-processed by
    other steps in your pipeline, then registers the model to MLFlow registry.

    Model training steps should have caching disabled if they are not deterministic
    (i.e. if the model training involve some random processes like initializing
    weights or shuffling data that are not controlled by setting a fixed random seed).

    Args:
        model: The model.
        tokenizer: The tokenizer.
        mlflow_model_name: Name of the model in MLFlow registry.

    Returns:
        The trained model and tokenizer.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    components = {
        "model": model,
        "tokenizer": tokenizer,
    }
    mlflow.transformers.log_model(
        transformers_model=components,
        artifact_path=mlflow_model_name,
        registered_model_name=mlflow_model_name,
        task="text-classification",
    )
    ### YOUR CODE ENDS HERE ###
