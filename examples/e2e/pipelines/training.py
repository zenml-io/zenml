#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import List, Optional

from config import DOCKER_SETTINGS, MetaConfig
from steps import (
    data_loader,
    model_evaluator,
    model_hp_tunning,
    model_trainer,
    notify_on_failure,
    notify_on_success,
    promote_model,
    train_data_preprocessor,
    train_data_splitter,
)

from zenml import pipeline
from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(
    settings={"docker": DOCKER_SETTINGS},
    on_success=notify_on_success,
    on_failure=notify_on_failure,
)
def e2e_example_training(
    test_size: float = 0.2,
    drop_na: Optional[bool] = None,
    normalize: Optional[bool] = None,
    drop_columns: Optional[List[str]] = None,
    hp_tunning_enabled: bool = True,
    random_seed: int = 42,
    min_train_accuracy: float = 0.0,
    min_test_accuracy: float = 0.0,
    fail_on_accuracy_quality_gates: bool = False,
):
    """
    Model training pipeline recipe.

    This is a recipe for a pipeline that loads the data, processes it and
    splits it into train and test sets, then trains and evaluates a model
    on it. It is agnostic of the actual step implementations and just defines
    how the artifacts are circulated through the steps by calling them in the
    right order and passing the output of one step as the input of the next
    step.

    The arguments that this function takes are instances of the steps that
    are defined in the steps folder. Also note that the arguments passed to
    the steps are step artifacts. If you use step parameters to configure the
    steps, they must not be used here, but instead be used when the steps are
    instantiated, before this function is called.

    Args:
        artifact_path_train: Path to train dataset on Artifact Store
        test_size: Size of holdout set for training 0.0..1.0
        drop_na: If `True` NA values will be removed from dataset
        normalize: If `True` dataset will be normalized with MinMaxScaler
        drop_columns: List of columns to drop from dataset
        hp_tunning_enabled: If `True` hyperparameter search would happen.
        random_seed: Seed of random generator,
        min_train_accuracy: Threshold to stop execution if train set accuracy is lower
        min_test_accuracy: Threshold to stop execution if test set accuracy is lower
        fail_on_accuracy_quality_gates: If `True` and `min_train_accuracy` or `min_test_accuracy`
            are not met - execution will be interrupted early

    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.

    ########## ETL stage ##########
    raw_data = data_loader(
        n_samples=100_000,
        drop_target=False,
    )
    dataset_trn, dataset_tst = train_data_splitter(
        dataset=raw_data,
        test_size=test_size,
    )
    dataset_trn, dataset_tst, _ = train_data_preprocessor(
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        drop_na=drop_na,
        normalize=normalize,
        drop_columns=drop_columns,
    )

    # HP #
    best_model_config = model_hp_tunning(
        hp_tunning_enabled=hp_tunning_enabled,
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
    )

    ########## Training stage ##########
    model = model_trainer(
        dataset_trn=dataset_trn,
        best_model_config=best_model_config,
        random_seed=random_seed,
    )
    model_evaluator(
        model=model,
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        min_train_accuracy=min_train_accuracy,
        min_test_accuracy=min_test_accuracy,
        fail_on_accuracy_quality_gates=fail_on_accuracy_quality_gates,
    )
    mlflow_register_model_step(
        model,
        name=MetaConfig.mlflow_model_name,
    )

    ########## Promotion stage ##########
    promote_model(
        dataset_tst=dataset_tst,
        after=["mlflow_register_model_step"],
    )
    ### YOUR CODE ENDS HERE ###
