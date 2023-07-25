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

from typing import Any, Dict, List, Optional

from config import MetaConfig
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression
from steps import (
    drift_na_count,
    inference_data_loader,
    inference_data_preprocessor,
    inference_predict,
    inference_save_results,
    model_evaluator,
    model_trainer,
    notify_on_failure,
    notify_on_success,
    promote_model,
    train_data_loader,
    train_data_preprocessor,
    train_data_splitter,
)

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import (
    AWS,
    EVIDENTLY,
    KUBEFLOW,
    KUBERNETES,
    MLFLOW,
    SKLEARN,
    SLACK,
)
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

docker_settings = DockerSettings(
    required_integrations=[
        AWS,
        EVIDENTLY,
        KUBEFLOW,
        KUBERNETES,
        MLFLOW,
        SKLEARN,
        SLACK,
    ],
)


@pipeline(
    settings={"docker": docker_settings},
    on_success=notify_on_success,
    on_failure=notify_on_failure,
    extra={"tag": "production"},
)
def e2e_example_pipeline(
    artifact_path_train: Optional[str] = None,
    artifact_path_inference: Optional[str] = None,
    test_size: float = 0.2,
    drop_na: Optional[bool] = None,
    normalize: Optional[bool] = None,
    drop_columns: Optional[List[str]] = None,
    model_class: ClassifierMixin = LogisticRegression,
    hyperparameters: Dict[str, Any] = None,
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
        artifact_path_inference: Path to inference dataset on Artifact Store
        test_size: Size of holdout sewt for training 0.0..1.0
        drop_na: If `True` NA values will be removed from dataset
        normalize: If `True` dataset will be normalized with MinMaxScaler
        drop_columns: List of columns to drop from dataset
        model_class: Class of model architecture to use on training
        hyperparameters: Dictonary of Hyperparameters passed to model init
        random_seed: Seed of randomizer
        min_train_accuracy: Threshold to stop execution if train set accuracy is lower
        min_test_accuracy: Threshold to stop execution if test set accuracy is lower
        fail_on_accuracy_quality_gates: If `True` and `min_train_accuracy` or `min_test_accuracy`
            are not met - execution will be interrupted early

    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.

    ########## ETL stage ##########
    raw_data = train_data_loader(artifact_path=artifact_path_train)
    dataset_trn, dataset_tst = train_data_splitter(
        dataset=raw_data,
        test_size=test_size,
    )
    (
        dataset_trn,
        dataset_tst,
        preprocess_pipeline,
    ) = train_data_preprocessor(
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        drop_na=drop_na,
        normalize=normalize,
        drop_columns=drop_columns,
    )

    ########## Training stage ##########
    model = model_trainer(
        dataset_trn=dataset_trn,
        model_class=model_class.__name__,
        hyperparameters=hyperparameters,
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
    model_version = promote_model(
        dataset_tst=dataset_tst,
        after=["mlflow_register_model_step"],
    )

    ########## Inference stage  ##########
    dataset_inf = inference_data_loader(
        artifact_path=artifact_path_inference,
        after=["promote_model"],
    )
    dataset_inf = inference_data_preprocessor(
        dataset_inf=dataset_inf,
        preprocess_pipeline=preprocess_pipeline,
    )
    predictions = inference_predict(
        dataset_inf=dataset_inf,
        model_version=model_version,
    )
    inference_save_results(
        predictions=predictions,
        path="/tmp/e2e_example.csv",
    )
    ########## DataQuality stage  ##########
    report, _ = evidently_report_step(
        reference_dataset=dataset_trn,
        comparison_dataset=dataset_inf,
        ignored_cols=["target"],
        suppress_missing_ignored_cols_error=True,
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )
    drift_na_count(report)
    ### YOUR CODE ENDS HERE ###

    # TODO:
    # - exchange `preprocess_pipeline` via MlFlow or artifact store
    # - !!! [?] add HP tunning
    # - [?] more real dataset loaded from artifact store or feature store (FS needs deploy and more effort)
    # - CustomMaterializer - future effort
    # - extra dict for pipeline config instead of pipeline.py
