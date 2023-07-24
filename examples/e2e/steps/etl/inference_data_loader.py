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

from typing import Annotated, Optional

import pandas as pd
from utils.misc import gen_data

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

artifact_store = Client().active_stack.artifact_store


@step
def inference_data_loader(
    artifact_path: Optional[str] = None,
) -> Annotated[pd.DataFrame, "dataset"]:
    """Dataset reader step.

    This is an example of a dataset reader step that reads the data from source
    so that it is suitable for inferece.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to read from S3 path or
    generate a random. See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        artifact_path: Path on Artifact Store with dataset in parquet format.

    Returns:
        The dataset artifact as Pandas DataFrame.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    if artifact_path:
        dataset = pd.read_parquet(path=artifact_path)
        logger.info(f"Dataset with {len(dataset)} records read from S3!")
    else:
        dataset = gen_data(n_samples=10_000)
        dataset.drop(columns=["target"], inplace=True)
        logger.info(f"Dataset with {len(dataset)} records generated!")
    ### YOUR CODE ENDS HERE ###
    return dataset
