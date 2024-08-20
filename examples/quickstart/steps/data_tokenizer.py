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
from typing import Annotated, Tuple

from datasets import Dataset
from materializers import T5Materializer
from transformers import (
    T5Tokenizer,
)

from steps.model_trainer import T5_Model
from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(
    output_materializers=[
        T5Materializer,
    ]
)
def tokenize_data(
    dataset: Dataset, model_type: T5_Model
) -> Tuple[
    Annotated[Dataset, "tokenized_dataset"],
    Annotated[T5Tokenizer, "tokenizer"],
]:
    """Tokenize the dataset."""
    tokenizer = T5Tokenizer.from_pretrained(model_type)

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

    return dataset.map(tokenize_function, batched=True), tokenizer
