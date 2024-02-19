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
import torch
import torch.nn as nn
from datasets import DatasetDict
from torch.utils.data import DataLoader
from transformers import DataCollatorWithPadding, PreTrainedTokenizerBase

from zenml import step


@step
def sequence_evaluator(
    model: nn.Module,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
    dummy_run: bool = True,
    batch_size: int = 8,
) -> float:
    """Evaluate trained model on validation set."""
    if dummy_run:
        return 0.0

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Define loss function
    loss_fn = nn.CrossEntropyLoss()

    # Convert into PyTorch dataset format
    validation_loader = DataLoader(
        tokenized_datasets["test"],
        batch_size=batch_size,
        shuffle=False,
        collate_fn=DataCollatorWithPadding(tokenizer, return_tensors="pt"),
    )

    model.eval()
    total_loss = 0.0
    total_samples = 0

    with torch.no_grad():
        for batch in validation_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = loss_fn(outputs.logits, labels)
            total_loss += loss.item() * labels.size(0)
            total_samples += labels.size(0)

    return total_loss / total_samples
