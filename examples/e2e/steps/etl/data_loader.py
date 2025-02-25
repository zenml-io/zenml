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


from typing import Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.datasets import load_breast_cancer
from typing_extensions import Annotated

from zenml import step, log_metadata
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def data_loader(
    random_state: int, is_inference: bool = False
) -> Tuple[
    Annotated[pd.DataFrame, "dataset"],
    Annotated[str, "target"],
    Annotated[int, "random_state"],
]:
    """Dataset reader step.

    This is an example of a dataset reader step that load Breast Cancer dataset.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured with number of rows and logic
    to drop target column or not. See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        is_inference: If `True` subset will be returned and target column
            will be removed from dataset.
        random_state: Random state for sampling

    Returns:
        The dataset artifact as Pandas DataFrame and name of target column.
    """
    # Load dataset
    dataset = load_breast_cancer(as_frame=True)
    inference_size = int(len(dataset.target) * 0.1)
    target = "target"
    dataset: pd.DataFrame = dataset.frame
    
    # Track original dataset metadata
    original_dataset_metadata = {
        "total_rows": int(len(dataset)),
        "total_columns": int(len(dataset.columns)),
        "missing_values": {col: int(val) for col, val in dataset.isnull().sum().to_dict().items()},
        "missing_percentage": {col: float(val) for col, val in (dataset.isnull().mean() * 100).to_dict().items()},
        "dataset_description": "Breast Cancer Wisconsin dataset from scikit-learn",
        "target_column": target,
        "target_distribution": {str(k): int(v) for k, v in dataset[target].value_counts().to_dict().items()},
        "timestamp": datetime.now().isoformat(),
    }
    
    # Log the original dataset metadata at the step level
    log_metadata({"original_dataset": original_dataset_metadata})
    
    # Create inference subset
    inference_subset = dataset.sample(
        inference_size, random_state=random_state
    )
    
    # Process dataset based on mode (inference or training)
    if is_inference:
        dataset = inference_subset
        dataset.drop(columns=target, inplace=True)
        
        # Track inference dataset metadata
        processed_dataset_metadata = {
            "dataset_type": "inference",
            "rows": int(len(dataset)),
            "random_state": int(random_state),
            "inference_size": int(inference_size),
        }
    else:
        dataset.drop(inference_subset.index, inplace=True)
        dataset.reset_index(drop=True, inplace=True)
        
        # Track training dataset metadata
        processed_dataset_metadata = {
            "dataset_type": "training",
            "rows": int(len(dataset)),
            "random_state": int(random_state),
            "target_distribution": {str(k): int(v) for k, v in dataset[target].value_counts().to_dict().items()},
        }
    
    # Log the processed dataset metadata at the step level
    log_metadata({"processed_dataset": processed_dataset_metadata})
    
    # Log metadata to the dataset artifact
    log_metadata(
        metadata={
            "dataset_info": processed_dataset_metadata,
            "source_info": {
                "source": "scikit-learn breast cancer dataset",
                "random_state": int(random_state),
                "is_inference": bool(is_inference),
                "timestamp": datetime.now().isoformat(),
            }
        },
        artifact_name="dataset",
        infer_artifact=True,
    )
        
    logger.info(f"Dataset with {len(dataset)} records loaded!")
    
    return dataset, target, random_state
