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
#

from datasets import DatasetDict
from transformers import PreTrainedTokenizerBase
from typing_extensions import Annotated
from utils.misc import find_max_length

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def tokenization_step(
    tokenizer: PreTrainedTokenizerBase,
    dataset: DatasetDict,
    padding: str = "max_length",
    max_seq_length: int = 512,
    text_column: str = "text",
    label_column: str = "label",
) -> Annotated[DatasetDict, "tokenized_data"]:
    """
    Tokenization step.

    This step tokenizes the dataset using the tokenizer and returns the tokenized
    dataset in a Huggingface DatasetDict format.

    Args:
        tokenizer: The tokenizer to use for tokenization.
        dataset: The dataset to be tokenized.
        padding: Padding strategy.
        max_seq_length: Maximum sequence length.
        text_column: Name of the text column.
        label_column: Name of the label column.

    Returns:
        The tokenized dataset.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    train_max_length = find_max_length(dataset["train"][text_column])

    # Depending on the dataset, find the maximum length of text in the validation or test dataset
    val_or_test_max_length = find_max_length(
        dataset["validation"][text_column]
    )
    max_length = (
        train_max_length
        if train_max_length >= val_or_test_max_length
        else val_or_test_max_length
    )
    logger.info(f"max length for the given dataset is:{max_length}")

    # Determine the maximum length for tokenization
    max_length = (
        train_max_length
        if train_max_length >= val_or_test_max_length
        else val_or_test_max_length
    )
    logger.info(f"max length for the given dataset is:{max_length}")

    def preprocess_function(examples):
        # Tokenize the examples with padding, truncation, and a specified maximum length
        result = tokenizer(
            examples[text_column],
            padding=padding,
            truncation=True,
            max_length=max_length or max_seq_length,
        )
        # Add labels to the tokenized examples
        result["label"] = examples[label_column]
        return result

    # Apply the preprocessing function to the dataset
    tokenized_datasets = dataset.map(
        preprocess_function,
        batched=True,
    )
    logger.info(tokenized_datasets)

    # Remove the original text column and rename the label column
    tokenized_datasets = tokenized_datasets.remove_columns([text_column])
    tokenized_datasets = tokenized_datasets.rename_column(
        label_column, "labels"
    )

    # Set the format of the tokenized dataset
    tokenized_datasets.set_format("torch")
    ### YOUR CODE ENDS HERE ###

    return tokenized_datasets
