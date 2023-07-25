#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import Annotated

import pandas as pd
from utils.misc import gen_data

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

artifact_store = Client().active_stack.artifact_store


@step
def data_loader(
    n_samples: int, drop_target: bool = False
) -> Annotated[pd.DataFrame, "dataset"]:
    """Dataset reader step.

    This is an example of a dataset reader step that generates random data for
    training or inference.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured with number of rows and logic
    to drop target column or not. See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        drop_target: If `True` `target` column will be removed from dataset.

    Returns:
        The dataset artifact as Pandas DataFrame.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    dataset = gen_data(n_samples=n_samples)
    if drop_target:
        dataset.drop(columns=["target"], inplace=True)
    logger.info(f"Dataset with {len(dataset)} records generated!")
    ### YOUR CODE ENDS HERE ###
    return dataset
