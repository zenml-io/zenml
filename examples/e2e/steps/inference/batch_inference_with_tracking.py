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

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, log_metadata, step
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentService,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def batch_inference_with_tracking(
    dataset_inf: pd.DataFrame,
    ground_truth_available: bool = False,
    batch_size: int = 1000,
) -> Tuple[
    Annotated[pd.DataFrame, ArtifactConfig(name="predictions_with_data")],
    Annotated[Dict[str, float], ArtifactConfig(name="inference_metrics")],
]:
    """Perform batch inference with extensive data tracking.

    This step takes a dataset for inference, runs predictions in batches,
    tracks detailed metadata about the inference process, and returns the
    predictions along with metrics. If ground truth is available in the dataset
    (in a column named 'target'), performance metrics will also be calculated.

    Args:
        dataset_inf: The inference dataset
        ground_truth_available: Whether ground truth values are available in the 'target' column
        batch_size: Size of batches for inference
        batch_id: Optional identifier for this batch inference run

    Returns:
        Tuple containing:
        - DataFrame with original data and predictions
        - Dictionary with inference metrics
    """
    # Start timing
    start_time = time.time()
    
    
    # Get model from context
    model = get_step_context().model
    logger.info(f"Running batch inference using model: {model.name} (version {model.version})")

    # Get predictor - first try deployment service, then fall back to loaded model
    logger.info("Using loaded model for predictions")
    predictor = model.load_artifact("model")
    def predict_method(data):
        return predictor.predict(data)
    source = "loaded_model"
    
    # Process in batches
    predictions_list = []
    batch_times = []
    batch_metrics = []
    
    # Copy the dataset to add predictions
    result_df = dataset_inf.copy()
    
    # Track if we have ground truth available
    has_target = ground_truth_available and "target" in dataset_inf.columns
    # Process in batches
    for i in range(0, len(dataset_inf), batch_size):
        batch_start_time = time.time()
        
        # Get the batch
        end_idx = min(i + batch_size, len(dataset_inf))
        batch = dataset_inf.iloc[i:end_idx]
        
        # Make predictions
        batch_predictions = predict_method(batch)
        
        # Store predictions
        predictions_list.append(batch_predictions)
        
        # Calculate batch processing time
        batch_end_time = time.time()
        batch_time = batch_end_time - batch_start_time
        batch_times.append(batch_time)
        
        # Log batch metrics
        batch_metrics.append({
            "batch_number": i // batch_size + 1,
            "batch_size": end_idx - i,
            "batch_processing_time": batch_time,
            "records_per_second": (end_idx - i) / batch_time if batch_time > 0 else 0,
        })
        
        logger.info(f"Processed batch {i // batch_size + 1}/{(len(dataset_inf) + batch_size - 1) // batch_size}")
    
    # Combine all predictions
    all_predictions = np.concatenate(predictions_list)
    result_df["predictions"] = all_predictions
    
    # End timing
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate performance metrics if ground truth is available
    performance_metrics = {}
    if has_target:
        y_true = dataset_inf["target"]
        y_pred = all_predictions
        
        performance_metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average="weighted")),
            "recall": float(recall_score(y_true, y_pred, average="weighted")),
            "f1_score": float(f1_score(y_true, y_pred, average="weighted")),
        }
    
    # Calculate predictions distribution
    pred_distribution = {}
    unique_preds, counts = np.unique(all_predictions, return_counts=True)
    for value, count in zip(unique_preds, counts):
        pred_distribution[str(value)] = int(count)
    
    # Prepare comprehensive metrics
    inference_metrics = {
        "total_records": int(len(dataset_inf)),
        "records_per_second": float(len(dataset_inf) / total_time) if total_time > 0 else 0,
        "average_batch_time": float(sum(batch_times) / len(batch_times)) if batch_times else 0,
        "prediction_distribution": pred_distribution,
        "inference_source": source,
        "model_name": model.name,
        "model_version": model.version,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Add performance metrics if available
    if performance_metrics:
        inference_metrics["performance_metrics"] = performance_metrics
    
    # Log all metadata
    log_metadata(
        metadata={
            "inference_metrics": inference_metrics,
            "batch_details": {f"batch_{i}": m for i, m in enumerate(batch_metrics)},
        }
    )
    
    # Log metadata to artifacts
    log_metadata(
        metadata={"inference_run": inference_metrics},
        artifact_name="predictions_with_data",
        infer_artifact=True,
    )
    
    # Log metadata to model
    log_metadata(
        metadata={
            "latest_inference_batch": {
                "records": int(len(dataset_inf)),
                "timestamp": datetime.now().isoformat(),
                "performance": performance_metrics if performance_metrics else {"available": False},
            }
        },
        infer_model=True,
    )
    
    # Log summary information
    logger.info(f"Batch inference completed for {len(dataset_inf)} records in {total_time:.2f} seconds")
    logger.info(f"Processing speed: {len(dataset_inf) / total_time:.2f} records/second")
    if performance_metrics:
        logger.info(f"Performance metrics: Accuracy={performance_metrics['accuracy']:.4f}, F1={performance_metrics['f1_score']:.4f}")
    return result_df, inference_metrics 