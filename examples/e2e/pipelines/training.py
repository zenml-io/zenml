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


import random
from typing import Any, Dict, List, Optional

from steps import (
    compute_performance_metrics_on_current_data,
    data_loader,
    hp_tuning_select_best_model,
    hp_tuning_single_search,
    model_evaluator,
    model_trainer,
    notify_on_failure,
    notify_on_success,
    promote_with_metric_compare,
    train_data_preprocessor,
    train_data_splitter,
)

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(on_failure=notify_on_failure)
def e2e_use_case_training(
    model_search_space: Dict[str, Any],
    target_env: str,
    test_size: float = 0.2,
    drop_na: Optional[bool] = None,
    normalize: Optional[bool] = None,
    drop_columns: Optional[List[str]] = None,
    min_train_accuracy: float = 0.0,
    min_test_accuracy: float = 0.0,
    fail_on_accuracy_quality_gates: bool = False,
):
    """
    Model training pipeline.

    This is a pipeline that loads the data, processes it and splits
    it into train and test sets, then search for best hyperparameters,
    trains and evaluates a model.

    Args:
        model_search_space: Search space for hyperparameter tuning
        target_env: The environment to promote the model to
        test_size: Size of holdout set for training 0.0..1.0
        drop_na: If `True` NA values will be removed from dataset
        normalize: If `True` dataset will be normalized with MinMaxScaler
        drop_columns: List of columns to drop from dataset
        min_train_accuracy: Threshold to stop execution if train set accuracy is lower
        min_test_accuracy: Threshold to stop execution if test set accuracy is lower
        fail_on_accuracy_quality_gates: If `True` and `min_train_accuracy` or `min_test_accuracy`
            are not met - execution will be interrupted early
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    ########## ETL stage ##########
    raw_data, target, _ = data_loader(random_state=random.randint(0, 100))
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
    ########## Hyperparameter tuning stage ##########
    after = []
    search_steps_prefix = "hp_tuning_search_"
    for config_name, model_search_configuration in model_search_space.items():
        step_name = f"{search_steps_prefix}{config_name}"
        hp_tuning_single_search(
            id=step_name,
            model_package=model_search_configuration["model_package"],
            model_class=model_search_configuration["model_class"],
            search_grid=model_search_configuration["search_grid"],
            dataset_trn=dataset_trn,
            dataset_tst=dataset_tst,
            target=target,
        )
        after.append(step_name)
    best_model = hp_tuning_select_best_model(step_names=after, after=after)

    ########## Training stage ##########
    model = model_trainer(
        dataset_trn=dataset_trn,
        model=best_model,
        target=target,
    )
    model_evaluator(
        model=model,
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        min_train_accuracy=min_train_accuracy,
        min_test_accuracy=min_test_accuracy,
        fail_on_accuracy_quality_gates=fail_on_accuracy_quality_gates,
        target=target,
    )
    ########## Promotion stage ##########
    (
        latest_metric,
        current_metric,
    ) = compute_performance_metrics_on_current_data(
        dataset_tst=dataset_tst,
        target_env=target_env,
        after=["model_evaluator"],
    )

    promote_with_metric_compare(
        latest_metric=latest_metric,
        current_metric=current_metric,
        target_env=target_env,
    )
    last_step = "promote_with_metric_compare"

    notify_on_success(after=[last_step])
    ### YOUR CODE ENDS HERE ###
