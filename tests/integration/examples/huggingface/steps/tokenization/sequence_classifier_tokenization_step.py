#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from datasets import DatasetDict
from transformers import PreTrainedTokenizerBase

from zenml import step


@step
def sequence_classifier_tokenization(
    tokenizer: PreTrainedTokenizerBase,
    datasets: DatasetDict,
    text_column: str = "text",
    label_column: str = "label",
    max_seq_length: int = 128,
) -> DatasetDict:
    """Tokenize dataset into tokens and then convert into encoded ids."""

    def preprocess_function(examples):
        result = tokenizer(
            examples[text_column],
            max_length=max_seq_length,
            truncation=True,
        )
        result["label"] = examples[label_column]
        return result

    tokenized_datasets = datasets.map(preprocess_function, batched=True)
    return tokenized_datasets
