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

from steps import (
    data_loader,
    drift_quality_gate,
    inference_data_preprocessor,
    inference_predict,
    notify_on_failure,
    notify_on_success,
)

from zenml import get_pipeline_context, pipeline
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(on_failure=notify_on_failure)
def e2e_use_case_batch_inference():
    """
    Model batch inference pipeline.

    This is a pipeline that loads the inference data, processes
    it, analyze for data drift and run inference.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    model = get_pipeline_context().model
    ########## ETL stage  ##########
    df_inference, target, _ = data_loader(
        random_state=model.get_artifact("random_state"), is_inference=True
    )
    df_inference = inference_data_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=model.get_artifact("preprocess_pipeline"),
        target=target,
    )
    ########## DataQuality stage  ##########
    report, _ = evidently_report_step(
        reference_dataset=model.get_artifact("dataset_trn"),
        comparison_dataset=df_inference,
        ignored_cols=["target"],
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )
    drift_quality_gate(report)
    ########## Inference stage  ##########
    inference_predict(
        dataset_inf=df_inference,
        after=["drift_quality_gate"],
    )

    notify_on_success(after=["inference_predict"])
    ### YOUR CODE ENDS HERE ###
