# 


import random
from typing import Any, Dict, List, Optional

from zenml import pipeline
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.logger import get_logger

from constants import DATA_CLASSIFICATION
from steps import (
    compute_performance_metrics_on_current_data,
    data_loader,
    model_evaluator,
    model_trainer,
    notify_on_failure,
    notify_on_success,
    promote_with_metric_compare,
    train_data_preprocessor,
    train_data_splitter,
)
from utils import get_model_from_config

logger = get_logger(__name__)


@pipeline(on_failure=notify_on_failure, tags=[DATA_CLASSIFICATION])
def supply_chain_forecast_training(
    model_configuration: Dict[str,Any],
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
        model_configuration: Configuration of the model to train
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
    raw_data, target, _ = data_loader(random_state=random.randint(0,100))
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
    best_model = get_model_from_config(
        model_package=model_configuration["model_package"], 
        model_class=model_configuration["model_class"],
        )(**model_configuration["params"])

    ########## Training stage ##########
    model = model_trainer(
        dataset_trn=dataset_trn,
        model=ExternalArtifact(value=best_model),
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
    latest_metric,current_metric = compute_performance_metrics_on_current_data(
        dataset_tst=dataset_tst,
        target_env=target_env,
        after=["model_evaluator"]
    )

    promote_with_metric_compare(
        latest_metric=latest_metric,
        current_metric=current_metric,
        target_env=target_env,
    )
    last_step = "promote_with_metric_compare"

    notify_on_success(after=[last_step])
    ### YOUR CODE ENDS HERE ###
