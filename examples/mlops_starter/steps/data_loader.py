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

"""Data loader step for both batch and serving use cases."""

from typing import List, Optional

import pandas as pd
from sklearn.datasets import load_breast_cancer
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def data_loader(
    random_state: int,
    is_inference: bool = False,
    target: str = "target",
    input_data: Optional[List[List[float]]] = None,
) -> Annotated[pd.DataFrame, "dataset"]:
    """Dataset reader step.

    This step can either load data from sklearn breast cancer dataset or
    accept input data directly for serving purposes.

    Args:
        random_state: Random state for sampling when loading from sklearn.
        is_inference: If `True` subset will be returned and target column
            will be removed from dataset.
        target: Name of target columns in dataset.
        input_data: Optional input data as list of feature vectors. If provided,
            this data will be used instead of loading from sklearn.

    Returns:
        The dataset artifact as Pandas DataFrame.
    """
    # Check if input data is provided directly
    if input_data is not None:
        # Use provided input data
        logger.info(
            f"Using provided input data with {len(input_data)} samples"
        )

        # Create DataFrame from input data
        # Breast cancer dataset has 30 features
        feature_names = [f"feature_{i}" for i in range(len(input_data[0]))]
        dataset = pd.DataFrame(input_data, columns=feature_names)

        logger.info(
            f"Dataset with {len(dataset)} records created from input data!"
        )
        return dataset

    # Load from sklearn dataset (original behavior)
    sklearn_dataset = load_breast_cancer(as_frame=True)
    inference_size = int(len(sklearn_dataset.target) * 0.05)
    dataset: pd.DataFrame = sklearn_dataset.frame
    inference_subset = dataset.sample(
        inference_size, random_state=random_state
    )
    if is_inference:
        dataset = inference_subset
        dataset.drop(columns=target, inplace=True)
    else:
        dataset.drop(inference_subset.index, inplace=True)
    dataset.reset_index(drop=True, inplace=True)
    logger.info(f"Dataset with {len(dataset)} records loaded from sklearn!")
    return dataset
