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
from typing import Any, Dict

import pandas as pd
from artifacts import ModelMetadata
from materializers import ModelMetadataMaterializer
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Perceptron, SGDClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC, LinearSVC
from sklearn.tree import DecisionTreeClassifier

from zenml.enums import StrEnum
from zenml.logger import get_logger
from zenml.steps import (
    BaseParameters,
    step,
)

logger = get_logger(__name__)


class SklearnClassifierModel(StrEnum):
    """Scikit-learn models used for classification."""

    LogisticRegression = "LogisticRegression"
    SVC = "SVC"
    LinearSVC = "LinearSVC"
    RandomForestClassifier = "RandomForestClassifier"
    KNeighborsClassifier = "KNeighborsClassifier"
    GaussianNB = "GaussianNB"
    Perceptron = "Perceptron"
    SGDClassifier = "SGDClassifier"
    DecisionTreeClassifier = "DecisionTreeClassifier"


class ModelTrainerStepParameters(BaseParameters):
    """Parameters for the model trainer step.

    This is an example of how to use step parameters to make your model trainer
    step configurable independently of the step code. This is useful for example
    if you want to try out different models in your pipeline without having to
    change the step code.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # The name of the scikit-learn classifier model to train.
    model: SklearnClassifierModel = SklearnClassifierModel.LogisticRegression
    # The random seed to use for reproducibility.
    random_state: int = 42
    # The parameters to pass to the model constructor.
    hyperparameters: Dict[str, Any] = {}
    ### YOUR CODE ENDS HERE ###

    class Config:
        """Pydantic config class.

        This is used to configure the behavior of Pydantic, the library used to
        parse and validate step parameters. See the documentation for more
        information:

            https://pydantic-docs.helpmanual.io/usage/model_config/

        It is recommended to explicitly forbid extra parameters here to ensure
        that the step parameters are always valid.
        """

        extra = "forbid"


@step
def model_trainer(
    params: ModelTrainerStepParameters,
    train_set: pd.DataFrame,
) -> ClassifierMixin:
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

    This step is parameterized using the `ModelTrainerStepParameters` class,
    which allows you to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use a different model, change the random seed, or pass different
    hyperparameters to the model constructor. See the documentation for more
    information:

        https://docs.zenml.io/starter-guide/pipelines/parameters-and-caching

    Args:
        params: The parameters for the model trainer step.
        train_set: The training data set artifact.

    Returns:
        The trained model artifact.
    """
    X_train = train_set.drop("target", axis=1)
    Y_train = train_set["target"]

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Initialize the model with the hyperparameters indicated in the step
    # parameters and train it on the training set.
    if params.model == SklearnClassifierModel.LogisticRegression:
        model = LogisticRegression(
            random_state=params.random_state,
            **params.hyperparameters,
        )
    elif params.model == SklearnClassifierModel.SVC:
        model = SVC(
            random_state=params.random_state,
            **params.hyperparameters,
        )
    elif params.model == SklearnClassifierModel.LinearSVC:
        model = LinearSVC(
            random_state=params.random_state,
            **params.hyperparameters,
        )
    elif params.model == SklearnClassifierModel.RandomForestClassifier:
        model = RandomForestClassifier(
            random_state=params.random_state,
            **params.hyperparameters,
        )
    elif params.model == SklearnClassifierModel.KNeighborsClassifier:
        model = KNeighborsClassifier(**params.hyperparameters)
    elif params.model == SklearnClassifierModel.GaussianNB:
        model = GaussianNB(**params.hyperparameters)
    elif params.model == SklearnClassifierModel.Perceptron:
        model = Perceptron(
            random_state=params.random_state,
            **params.hyperparameters,
        )
    elif params.model == SklearnClassifierModel.SGDClassifier:
        model = SGDClassifier(
            random_state=params.random_state, **params.hyperparameters
        )
    elif params.model == SklearnClassifierModel.DecisionTreeClassifier:
        model = DecisionTreeClassifier(
            random_state=params.random_state,
            **params.hyperparameters,
        )

    logger.info(f"Training model {model}...")
    model.fit(X_train, Y_train)
    ### YOUR CODE ENDS HERE ###

    return model


class ModelEvaluatorStepParameters(BaseParameters):
    """Parameters for the model evaluator step.

    This is an example of how to use step parameters to make your model
    evaluator step configurable independently of the step code. This is useful
    for example if you want to control the acceptable thresholds for your model
    metrics in your pipeline without having to change the step code.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # The minimum acceptable accuracy on the train set.
    min_train_accuracy: float = 0.8
    # The minimum acceptable accuracy on the test set.
    min_test_accuracy: float = 0.8
    # The maximum acceptable difference between train and test accuracy.
    max_train_test_accuracy_difference: float = 0.1
    # Whether to raise an error and fail the pipeline step if the model
    # performance does not meet the minimum criteria.
    fail_on_warnings: bool = False
    ### YOUR CODE ENDS HERE ###

    class Config:
        """Pydantic config class.

        This is used to configure the behavior of Pydantic, the library used to
        parse and validate step parameters. See the documentation for more
        information:

            https://pydantic-docs.helpmanual.io/usage/model_config/

        It is recommended to explicitly forbid extra parameters here to ensure
        that the step parameters are always valid.
        """

        extra = "forbid"


@step(output_materializers=ModelMetadataMaterializer)
def model_evaluator(
    params: ModelEvaluatorStepParameters,
    model: ClassifierMixin,
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ModelMetadata:
    """Evaluate a trained model.

    This is an example of a model evaluation step that takes in a model artifact
    previously trained by another step in your pipeline, and a training
    and validation data set pair which it uses to evaluate the model's
    performance. The step returns a custom type of artifact containing metadata
    about the trained model. Note that using a custom data type also requires
    implementing a custom materializer for it. See the `materializer` folder
    or the following ZenML docs for more information about materializers:

        https://docs.zenml.io/advanced-guide/pipelines/materializers

    The suggested step implementation also outputs some warnings if the model
    performance does not meet some minimum criteria. This is just an example of
    how you can use steps to monitor your model performance and alert you if
    something goes wrong. As an alternative, you can raise an exception in the
    step to force the pipeline run to fail early and all subsequent steps to
    be skipped.

    This step is parameterized using the `ModelEvaluatorStepParameters` class,
    which allows you to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use different values for the acceptable model performance thresholds and
    to control whether the pipeline run should fail if the model performance
    does not meet the minimum criteria. See the documentation for more
    information:

        https://docs.zenml.io/starter-guide/pipelines/parameters-and-caching

    Args:
        params: The parameters for the model evaluator step.
        model: The pre-trained model artifact.
        train_set: The training data set artifact.
        test_set: The test data set artifact.

    Returns:
        A model metadata artifact.
    """
    X_train = train_set.drop("target", axis=1)
    Y_train = train_set["target"]
    X_test = test_set.drop("target", axis=1)
    Y_test = test_set["target"]

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Calculate the model accuracy on the train and test set
    train_acc = model.score(X_train, Y_train)
    logger.info(f"Train accuracy: {train_acc}")
    test_acc = model.score(X_test, Y_test)
    logger.info(f"Test accuracy: {test_acc}")

    messages = []
    if train_acc < params.min_train_accuracy:
        messages.append(
            f"Train accuracy is below {params.min_train_accuracy*100}% !"
        )
    if test_acc < params.min_test_accuracy:
        messages.append(
            f"Test accuracy is below {params.min_test_accuracy*100}% !"
        )
    if test_acc - train_acc > params.max_train_test_accuracy_difference:
        messages.append(
            f"Train accuracy is more than "
            f"{params.max_train_test_accuracy_difference*100}% "
            f"higher than test accuracy. The model is overfitting the training "
            f"dataset."
        )
    if params.fail_on_warnings and messages:
        raise RuntimeError(
            "Model performance did not meet the minimum criteria:\n"
            + "\n".join(messages)
        )
    else:
        for message in messages:
            logger.warning(message)

    model_metadata = ModelMetadata()
    model_metadata.collect_metadata(
        model=model,
        train_accuracy=train_acc,
        test_accuracy=test_acc,
    )
    return model_metadata
    ### YOUR CODE ENDS HERE ###


@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model
