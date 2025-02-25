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

from steps import (
    data_loader,
    drift_quality_gate,
    inference_data_preprocessor,
    notify_on_failure,
    notify_on_success,
)
from steps.inference.batch_inference_with_tracking import batch_inference_with_tracking

from zenml import get_pipeline_context, log_metadata, pipeline, step
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step
from zenml.logger import get_logger
from datetime import datetime
import os
import pandas as pd

logger = get_logger(__name__)


@step
def save_inference_results(
    predictions: pd.DataFrame,
    metrics: dict,
    output_path: str = None,
):
    """Save inference results to a file.
    
    Args:
        predictions: DataFrame with predictions
        metrics: Dictionary with inference metrics
        output_path: Path to save results to (defaults to timestamped CSV in current directory)
    """
    # Generate default path if none provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"inference_results_{timestamp}.csv"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # Save predictions to CSV
    predictions.to_csv(output_path, index=False)
    logger.info(f"Saved inference results to {output_path}")
    
    # Log the output path to metadata
    log_metadata({
        "output_details": {
            "path": output_path,
            "format": "csv",
            "size_bytes": os.path.getsize(output_path),
            "row_count": len(predictions),
            "timestamp": datetime.now().isoformat(),
        }
    })
    
    # Log summary metrics for quick access
    prediction_distribution = {}
    if "predictions" in predictions:
        value_counts = predictions["predictions"].value_counts().to_dict()
        prediction_distribution = {str(k): int(v) for k, v in value_counts.items()}
    
    log_metadata({
        "results_summary": {
            "total_records": int(len(predictions)),
            "prediction_distribution": prediction_distribution,
            "path": output_path,
        }
    })
    
    return output_path