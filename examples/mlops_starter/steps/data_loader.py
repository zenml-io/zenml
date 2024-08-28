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

import pandas as pd
from sklearn.datasets import load_breast_cancer
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def data_loader(
    random_state: int, is_inference: bool = False, target: str = "target"
) -> Annotated[pd.DataFrame, "dataset"]:
    """Dataset reader step.

    This is an example of a dataset reader step that load Breast Cancer dataset.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured with number of rows and logic
    to drop target column or not. See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        random_state: Random state for sampling
        is_inference: If `True` subset will be returned and target column
            will be removed from dataset.
        target: Name of target columns in dataset.

    Returns:
        The dataset artifact as Pandas DataFrame and name of target column.
    """
    dataset = load_breast_cancer(as_frame=True)
    inference_size = int(len(dataset.target) * 0.05)
    dataset: pd.DataFrame = dataset.frame
    inference_subset = dataset.sample(
        inference_size, random_state=random_state
    )
    if is_inference:
        dataset = inference_subset
        dataset.drop(columns=target, inplace=True)
    else:
        dataset.drop(inference_subset.index, inplace=True)
    dataset.reset_index(drop=True, inplace=True)
    logger.info(f"Dataset with {len(dataset)} records loaded!")
    return dataset
