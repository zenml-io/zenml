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

from datasets import DatasetDict, load_dataset
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def data_loader() -> Annotated[DatasetDict, "dataset"]:
    """
    Data loader step.

    This step reads data from a Huggingface dataset or a CSV files and returns
    a Huggingface dataset.

    Data loader steps should have caching disabled if they are not deterministic
    (i.e. if they data they load from the external source can be different when
    they are subsequently called, even if the step code and parameter values
    don't change).

    Returns:
        The loaded dataset artifact.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    logger.info("Loading dataset airline_reviews... ")

    # Load dataset based on the dataset value
    dataset = load_dataset(
        "Shayanvsf/US_Airline_Sentiment",
        trust_remote_code=True,
    )
    dataset = dataset.rename_column("airline_sentiment", "label")
    dataset = dataset.remove_columns(
        ["airline_sentiment_confidence", "negativereason_confidence"]
    )

    # Log the dataset and sample examples
    logger.info(dataset)
    logger.info(
        f"Sample Example 1 : {dataset['train'][0]['text']} with label {dataset['train'][0]['label']}"
    )
    logger.info(
        f"Sample Example 1 : {dataset['train'][1]['text']} with label {dataset['train'][1]['label']}"
    )
    logger.info("Dataset Loaded Successfully")
    ### YOUR CODE ENDS HERE ###

    return dataset
