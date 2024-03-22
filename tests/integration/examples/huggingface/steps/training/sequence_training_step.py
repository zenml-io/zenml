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
from typing import Union

import torch
import torch.nn as nn
from datasets import DatasetDict
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    PreTrainedTokenizerBase,
)

from zenml import step


@step
def sequence_trainer(
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
    pretrained_model: str = "dhpollack/distilbert-dummy-sentiment",
    epochs: int = 1,
    batch_size: int = 8,
    init_lr: float = 2e-5,
    weight_decay_rate: float = 0.01,
    dummy_run: bool = True,
) -> Union[AutoModelForSequenceClassification, nn.Module]:
    """Build and Train token classification model."""
    # Get label list
    label_list = tokenized_datasets["train"].unique("label")

    # Load pre-trained model from huggingface hub
    model = AutoModelForSequenceClassification.from_pretrained(
        pretrained_model, num_labels=len(label_list)
    )

    if dummy_run:
        return model

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Define optimizer and loss function
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=init_lr, weight_decay=weight_decay_rate
    )

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        # Prepare dataloader
        train_loader = DataLoader(
            tokenized_datasets["train"], batch_size=batch_size, shuffle=True
        )

        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss
            total_loss += loss.item()

            loss.backward()
            optimizer.step()

        print(
            f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss / len(train_loader)}"
        )

    return model
