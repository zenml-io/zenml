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


from config import DEFAULT_PIPELINE_EXTRAS, PIPELINE_SETTINGS, MetaConfig
from steps import (
    data_loader,
    drift_quality_gate,
    inference_data_preprocessor,
    inference_get_current_version,
    inference_predict,
    notify_on_failure,
    notify_on_success,
)

from zenml import pipeline
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(
    settings=PIPELINE_SETTINGS,
    on_failure=notify_on_failure,
    extra=DEFAULT_PIPELINE_EXTRAS,
)
def e2e_use_case_batch_inference():
    """
    Model batch inference pipeline.

    This is a pipeline that loads the inference data, processes
    it, analyze for data drift and run inference.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    ########## ETL stage  ##########
    df_inference, target = data_loader(is_inference=True)
    df_inference = inference_data_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=ExternalArtifact(
            pipeline_name=MetaConfig.pipeline_name_training,
            artifact_name="preprocess_pipeline",
        ),
        target=target,
    )
    ########## DataQuality stage  ##########
    report, _ = evidently_report_step(
        reference_dataset=ExternalArtifact(
            pipeline_name=MetaConfig.pipeline_name_training,
            artifact_name="dataset_trn",
        ),
        comparison_dataset=df_inference,
        ignored_cols=["target"],
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )
    drift_quality_gate(report)
    ########## Inference stage  ##########
    registry_model_version = inference_get_current_version()
    deployment_service = mlflow_model_registry_deployer_step(
        registry_model_name=MetaConfig.mlflow_model_name,
        registry_model_version=registry_model_version,
        replace_existing=False,
    )
    inference_predict(
        deployment_service=deployment_service,
        dataset_inf=df_inference,
        after=["drift_quality_gate"],
    )

    notify_on_success(after=["inference_predict"])
    ### YOUR CODE ENDS HERE ###
