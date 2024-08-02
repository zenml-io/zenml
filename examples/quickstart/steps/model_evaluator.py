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
import torch
from datasets import Dataset
from transformers import (
    T5ForConditionalGeneration,
)

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def evaluate_model(
    model: T5ForConditionalGeneration, tokenized_dataset: Dataset
) -> None:
    """Evaluate the model on the training dataset."""
    model.eval()
    total_loss = 0
    num_batches = 0

    for i in range(0, len(tokenized_dataset), 8):  # batch size of 8
        batch = tokenized_dataset[i : i + 8]
        inputs = {
            "input_ids": torch.tensor(batch["input_ids"]),
            "attention_mask": torch.tensor(batch["attention_mask"]),
            "labels": torch.tensor(batch["labels"]),
        }
        with torch.no_grad():
            outputs = model(**inputs)
        total_loss += outputs.loss.item()
        num_batches += 1

    avg_loss = total_loss / num_batches
    print(f"Average loss on the dataset: {avg_loss}")
