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

from typing import List, Optional

from steps import (
    data_loader,
    data_preprocessor,
    data_splitter,
)

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def feature_engineering(
    test_size: float = 0.2,
    drop_na: Optional[bool] = None,
    normalize: Optional[bool] = None,
    drop_columns: Optional[List[str]] = None,
    target: Optional[str] = "target",
    random_state: int = 17,
):
    """
    Feature engineering pipeline.

    This is a pipeline that loads the data, processes it and splits
    it into train and test sets.

    Args:
        test_size: Size of holdout set for training 0.0..1.0
        drop_na: If `True` NA values will be removed from dataset
        normalize: If `True` dataset will be normalized with MinMaxScaler
        drop_columns: List of columns to drop from dataset
        target: Name of target column in dataset
        random_state: Random state to configure the data loader

    Returns:
        The processed datasets (dataset_trn, dataset_tst).
    """
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    raw_data = data_loader(random_state=random_state, target=target)
    dataset_trn, dataset_tst = data_splitter(
        dataset=raw_data,
        test_size=test_size,
    )
    dataset_trn, dataset_tst, _ = data_preprocessor(
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        drop_na=drop_na,
        normalize=normalize,
        drop_columns=drop_columns,
        target=target,
        random_state=random_state,
    )
    return dataset_trn, dataset_tst
