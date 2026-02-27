# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
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
"""CNN model for FashionMNIST classification."""

import torch
from lightning import LightningModule


class FashionMNISTClassifier(LightningModule):
    """Simple CNN for FashionMNIST classification."""

    def __init__(self, learning_rate: float, hidden_dim: int):
        super().__init__()
        self.save_hyperparameters()
        self.learning_rate = learning_rate

        self.model = torch.nn.Sequential(
            # Input: 1x28x28
            torch.nn.Conv2d(1, hidden_dim, kernel_size=3, padding=1),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),  # 14x14
            torch.nn.Conv2d(
                hidden_dim, hidden_dim * 2, kernel_size=3, padding=1
            ),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),  # 7x7
            torch.nn.Flatten(),
            torch.nn.Linear(hidden_dim * 2 * 7 * 7, 64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(64, 10),
        )
        self.loss_fn = torch.nn.CrossEntropyLoss()

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.loss_fn(logits, y)
        acc = (logits.argmax(1) == y).float().mean()
        self.log("train_loss", loss, prog_bar=True)
        self.log("train_acc", acc, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.loss_fn(logits, y)
        acc = (logits.argmax(1) == y).float().mean()
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", acc, prog_bar=True)
        return {"val_loss": loss, "val_acc": acc}

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.learning_rate)
