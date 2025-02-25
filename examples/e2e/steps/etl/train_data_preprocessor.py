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


from typing import List, Optional, Tuple
from datetime import datetime
import time

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from typing_extensions import Annotated
from utils.preprocess import ColumnsDropper, DataFrameCaster, NADropper

from zenml import step, log_metadata
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_data_preprocessor(
    dataset_trn: pd.DataFrame,
    dataset_tst: pd.DataFrame,
    drop_na: Optional[bool] = None,
    normalize: Optional[bool] = None,
    drop_columns: Optional[List[str]] = None,
) -> Tuple[
    Annotated[pd.DataFrame, "dataset_trn"],
    Annotated[pd.DataFrame, "dataset_tst"],
    Annotated[Pipeline, "preprocess_pipeline"],
]:
    """Data preprocessor step.

    This is an example of a data processor step that prepares the data so that
    it is suitable for model training. It takes in a dataset as an input step
    artifact and performs any necessary preprocessing steps like cleaning,
    feature engineering, feature selection, etc. It then returns the processed
    dataset as an step output artifact.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to drop NA values, drop some
    columns and normalize numerical columns. See the documentation for more
    information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        dataset_trn: The train dataset.
        dataset_tst: The test dataset.
        drop_na: If `True` all NA rows will be dropped.
        normalize: If `True` all numeric fields will be normalized.
        drop_columns: List of column names to drop.

    Returns:
        The processed datasets (dataset_trn, dataset_tst) and fitted `Pipeline` object.
    """
    # Start timing for preprocessing
    start_time = time.time()
    
    # Capture input data stats - Convert NumPy types to standard Python types
    input_data_stats = {
        "train_dataset_shape": tuple(int(x) for x in dataset_trn.shape),
        "test_dataset_shape": tuple(int(x) for x in dataset_tst.shape),
        "train_missing_values": int(dataset_trn.isnull().sum().sum()),
        "test_missing_values": int(dataset_tst.isnull().sum().sum()),
        "train_missing_percentage": float(dataset_trn.isnull().mean().mean() * 100),
        "test_missing_percentage": float(dataset_tst.isnull().mean().mean() * 100),
        "preprocessing_params": {
            "drop_na": drop_na,
            "normalize": normalize,
            "drop_columns": drop_columns if drop_columns else [],
        }
    }
    
    # Log preprocessing input parameters and stats
    log_metadata({"preprocessing_input": input_data_stats})

    # Build the preprocessing pipeline
    preprocess_pipeline = Pipeline([("passthrough", "passthrough")])
    
    # Track transformations applied
    transformations = []
    
    if drop_na:
        preprocess_pipeline.steps.append(("drop_na", NADropper()))
        transformations.append("drop_na")
        
    if drop_columns:
        # Drop columns
        preprocess_pipeline.steps.append(
            ("drop_columns", ColumnsDropper(drop_columns))
        )
        transformations.append(f"drop_columns: {drop_columns}")
        
    if normalize:
        # Normalize the data
        preprocess_pipeline.steps.append(("normalize", MinMaxScaler()))
        transformations.append("normalize_with_minmax_scaler")
        
    preprocess_pipeline.steps.append(
        ("cast", DataFrameCaster(dataset_trn.columns))
    )
    transformations.append("dataframe_casting")
    
    # Apply transformations
    dataset_trn_processed = preprocess_pipeline.fit_transform(dataset_trn)
    dataset_tst_processed = preprocess_pipeline.transform(dataset_tst)
    
    # Calculate preprocessing time
    preprocessing_time = time.time() - start_time
    
    # Track the statistics after preprocessing - Convert NumPy types to standard Python types
    output_data_stats = {
        "train_processed_shape": tuple(int(x) for x in dataset_trn_processed.shape),
        "test_processed_shape": tuple(int(x) for x in dataset_tst_processed.shape),
        "train_rows_removed": int(dataset_trn.shape[0] - dataset_trn_processed.shape[0]),
        "columns_removed": int(dataset_trn.shape[1] - dataset_trn_processed.shape[1]),
        "train_missing_values_after": int(dataset_trn_processed.isnull().sum().sum()),
        "test_missing_values_after": int(dataset_tst_processed.isnull().sum().sum()),
        "transformations_applied": transformations,
        "preprocessing_time_seconds": float(preprocessing_time),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Calculate column statistics after preprocessing for numerical columns - Convert NumPy types to standard Python types
    column_stats = {}
    for col in dataset_trn_processed.select_dtypes(include=[np.number]).columns:
        column_stats[col] = {
            "min": float(dataset_trn_processed[col].min()),
            "max": float(dataset_trn_processed[col].max()),
            "mean": float(dataset_trn_processed[col].mean()),
            "std": float(dataset_trn_processed[col].std()),
        }
    
    output_data_stats["column_statistics"] = column_stats
    
    # Log the preprocessing output statistics
    log_metadata({"preprocessing_output": output_data_stats})
    
    # Log metadata to the processed datasets
    log_metadata(
        metadata={
            "preprocessing_summary": {
                "input_shapes": {
                    "train": tuple(int(x) for x in dataset_trn.shape),
                    "test": tuple(int(x) for x in dataset_tst.shape),
                },
                "output_shapes": {
                    "train": tuple(int(x) for x in dataset_trn_processed.shape),
                    "test": tuple(int(x) for x in dataset_tst_processed.shape),
                },
                "transformations": transformations,
                "processing_time": float(preprocessing_time),
            }
        },
        artifact_name="dataset_trn",
        infer_artifact=True,
    )
    
    log_metadata(
        metadata={
            "preprocessing_summary": {
                "input_shapes": {
                    "train": tuple(int(x) for x in dataset_trn.shape),
                    "test": tuple(int(x) for x in dataset_tst.shape),
                },
                "output_shapes": {
                    "train": tuple(int(x) for x in dataset_trn_processed.shape),
                    "test": tuple(int(x) for x in dataset_tst_processed.shape),
                },
                "transformations": transformations,
                "processing_time": float(preprocessing_time),
            }
        },
        artifact_name="dataset_tst",
        infer_artifact=True,
    )
    
    # Log pipeline info to the pipeline artifact
    log_metadata(
        metadata={
            "pipeline_info": {
                "steps": [step[0] for step in preprocess_pipeline.steps],
                "transformations": transformations,
            }
        },
        artifact_name="preprocess_pipeline",
        infer_artifact=True,
    )
    
    # Log important information
    logger.info(f"Preprocessing completed in {preprocessing_time:.2f} seconds")
    logger.info(f"Train dataset: {dataset_trn.shape} -> {dataset_trn_processed.shape}")
    logger.info(f"Test dataset: {dataset_tst.shape} -> {dataset_tst_processed.shape}")
    if transformations:
        logger.info(f"Applied transformations: {', '.join(transformations)}")

    return dataset_trn_processed, dataset_tst_processed, preprocess_pipeline
