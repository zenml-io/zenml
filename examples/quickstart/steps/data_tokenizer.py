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
from datasets import Dataset
from transformers import (
    T5Tokenizer,
)

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def tokenize_data(dataset: Dataset) -> Dataset:
    """Tokenize the dataset."""
    tokenizer = T5Tokenizer.from_pretrained("t5-small")

    def tokenize_function(examples):
        model_inputs = tokenizer(
            examples["input"],
            max_length=128,
            truncation=True,
            padding="max_length",
        )
        labels = tokenizer(
            examples["target"],
            max_length=128,
            truncation=True,
            padding="max_length",
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    return dataset.map(tokenize_function, batched=True)
