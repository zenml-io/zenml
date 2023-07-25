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

from typing import Optional

from config import MetaConfig, PipelinesConfig
from steps import (
    data_loader,
    drift_na_count,
    inference_data_preprocessor,
    inference_predict,
    notify_on_failure,
    notify_on_success,
)
from utils.artifacts import find_artifact_id

from zenml import pipeline
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.logger import get_logger
from zenml.steps.external_artifact import ExternalArtifact

logger = get_logger(__name__)


@pipeline(
    settings={"docker": PipelinesConfig.docker_settings},
    on_success=notify_on_success,
    on_failure=notify_on_failure,
)
def e2e_example_batch_inference(
    artifact_path_inference: Optional[str] = None,
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
        artifact_path_inference: Path to inference dataset on Artifact Store

    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    ########## ETL stage  ##########
    dataset_inf = data_loader(
        n_samples=10_000,
        drop_target=True,
    )
    preprocess_pipeline_id = find_artifact_id(
        pipeline_name=MetaConfig.pipeline_name_training,
        artifact_name="preprocess_pipeline",
    )
    dataset_inf = inference_data_preprocessor(
        dataset_inf=dataset_inf,
        preprocess_pipeline=ExternalArtifact(id=preprocess_pipeline_id),
    )

    ########## DataQuality stage  ##########
    dataset_trn_id = find_artifact_id(
        pipeline_name=MetaConfig.pipeline_name_training,
        artifact_name="dataset_trn",
    )
    report, _ = evidently_report_step(
        reference_dataset=ExternalArtifact(id=dataset_trn_id),
        comparison_dataset=dataset_inf,
        ignored_cols=["target"],
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )
    drift_na_count(report)

    ########## Inference stage  ##########
    model_version_id = find_artifact_id(
        pipeline_name=MetaConfig.pipeline_name_training,
        artifact_name="model_version",
    )
    inference_predict(
        dataset_inf=dataset_inf,
        model_version=ExternalArtifact(id=model_version_id),
        after=["drift_na_count"],
    )
    ### YOUR CODE ENDS HERE ###
