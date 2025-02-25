# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
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

import os
from datetime import datetime

import pandas as pd
from steps import (
    data_loader,
    drift_quality_gate,
    inference_data_preprocessor,
    notify_on_failure,
    notify_on_success,
    save_inference_results,
)
from steps.inference.batch_inference_with_tracking import (
    batch_inference_with_tracking,
)

from zenml import get_pipeline_context, log_metadata, pipeline, step
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(on_failure=notify_on_failure, enable_cache=False)
def e2e_use_case_batch_inference(
    batch_size: int = 1000,
    ground_truth_available: bool = False,
    output_path: str = None,
):
    """Enhanced model batch inference pipeline with data tracking.

    This pipeline loads inference data, processes it, analyzes for data drift,
    runs batch inference with detailed tracking, and saves the results to a file.
    
    Args:
        batch_size: Size of batches for processing
        ground_truth_available: Whether ground truth values are available
        output_path: Optional path to save results
    """
    # Get model from pipeline context
    model = get_pipeline_context().model
    
    # ETL stage: Load and preprocess data
    df_inference, target, _ = data_loader(
        random_state=model.get_artifact("random_state"), 
        is_inference=True
    )
    
    # Preprocess the inference data
    df_inference = inference_data_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=model.get_artifact("preprocess_pipeline"),
        target=target,
    )
    
    # Data Quality stage: Check for data drift
    report, _ = evidently_report_step(
        reference_dataset=model.get_artifact("dataset_trn"),
        comparison_dataset=df_inference,
        ignored_cols=["target"],
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
            EvidentlyMetricConfig.metric("DataDriftPreset"),
        ],
    )
    
    # Data quality gate to catch significant drift
    drift_quality_gate(report)
    
    # Inference stage with tracking
    predictions, metrics = batch_inference_with_tracking(
        dataset_inf=df_inference,
        ground_truth_available=ground_truth_available,
        batch_size=batch_size,
        after=["drift_quality_gate"],
    )
    
    # Save results
    results_path = save_inference_results(
        predictions=predictions,
        metrics=metrics,
        output_path=output_path,
    )
    
    # Notify on success
    notify_on_success(after=["save_inference_results"])
