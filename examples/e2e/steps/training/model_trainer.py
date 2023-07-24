from typing import Annotated, Any, Dict, Optional

import mlflow
import pandas as pd
from sklearn.base import ClassifierMixin

from steps.training.common import (
    TARGET_COLUMN,
    experiment_tracker,
    logger,
    supported_models,
)
from zenml import step


@step(experiment_tracker=experiment_tracker.name)
def model_trainer(
    dataset_trn: pd.DataFrame,
    model_class: str = "LogisticRegression",
    hyperparameters: Optional[Dict[str, Any]] = None,
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
        model_class: Name of a model architecture class to train with.
        hyperparameters: Dictionary of initialization parameters to pass to the model class.
        random_seed: Fixed seed of randomizer.

    Returns:
        The trained model artifact.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Initialize the model with the hyperparameters indicated in the step
    # parameters and train it on the training set.
    hyperparameters = hyperparameters or {}
    model_class = supported_models.get(model_class)
    if "random_seed" in model_class.__init__.__code__.co_varnames:
        model = model_class(random_seed=random_seed, **hyperparameters)
    else:
        model = model_class(**hyperparameters)

    logger.info(f"Training model {model}...")
    mlflow.sklearn.autolog()
    model.fit(
        dataset_trn.drop(columns=[TARGET_COLUMN]), dataset_trn[TARGET_COLUMN]
    )
    ### YOUR CODE ENDS HERE ###

    return model
