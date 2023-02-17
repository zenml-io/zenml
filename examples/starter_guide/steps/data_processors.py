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

import pandas as pd
from sklearn.datasets import (
    load_wine,
)
from sklearn.model_selection import train_test_split

from zenml.logger import get_logger
from zenml.steps import (
    Output,
    step,
)

logger = get_logger(__name__)


@step
def simple_data_splitter() -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame):
    """Load and split a dataset."""
    # Load the wine dataset
    logger.info("Loading wine dataset!")
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set
