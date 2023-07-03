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

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchmetrics import Accuracy

from pytorch_lightning import LightningModule, Trainer
from torch.nn import functional as F
from zenml import step

from steps.importers import load_model



class CustomModel(  # pylint: disable = (abstract-method, too-many-ancestors, too-many-instance-attributes)
    LightningModule
):
    """Model to classify MNIST images."""

    def __init__(
        self,
        model: nn.Module,
        num_labels: int,
        dataloader_train: DataLoader,
        dataloader_test: DataLoader,
        dataloader_val: DataLoader,
        learning_rate: float = 2e-4,
    ):
        """Initialize class.
        Args:
            model: Model to train.
            num_labels: Number of classes to classify.
            dataloader_train: Training dataloader.
            dataloader_test: Test dataloader.
            learning_rate: Learning rate parameter. Defaults to 2e-4.
        """

        super().__init__()

        # Set our init args as class attributes
        self.learning_rate = learning_rate

        # Hardcode some dataset specific attributes
        self.model = model
        self.num_classes = num_labels

        self.dataloader_train = dataloader_train
        self.dataloader_test = dataloader_test
        self.dataloader_val = dataloader_val

        self.val_accuracy = Accuracy(task="multiclass", num_classes=self.num_classes)
        self.test_accuracy = Accuracy(task="multiclass", num_classes=self.num_classes)

    def forward(  # pylint: disable = (arguments-differ)
        self, x: torch.Tensor
    ) -> torch.Tensor:
        x = self.model(x)
        return F.log_softmax(x, dim=1)

    def training_step(  # pylint: disable = (arguments-differ)
        self,
        batch: torch.Tensor,
        batch_idx: int,  # pylint: disable = (unused-argument)
    ) -> torch.Tensor:
        samples, targets = batch
        logits = self(samples)
        loss = F.nll_loss(logits, targets)
        return loss

    def validation_step(  # pylint: disable = (arguments-differ)
        self,
        batch: torch.Tensor,
        batch_idx: int,  # pylint: disable = (unused-argument)
    ) -> None:
        samples, targets = batch
        logits = self(samples)
        loss = F.nll_loss(logits, targets)
        preds = torch.argmax(logits, dim=1)  # pylint: disable = (no-member)
        self.val_accuracy.update(preds, targets)  # pylint: disable = (no-member)

        # Calling self.log will surface up scalars for you in TensorBoard
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", self.val_accuracy, prog_bar=True)

    def test_step(  # pylint: disable = (arguments-differ)
        self,
        batch: torch.Tensor,
        batch_idx: int,  # pylint: disable = (unused-argument)
    ) -> None:
        samples, targets = batch
        logits = self(samples)
        loss = F.nll_loss(logits, targets)
        preds = torch.argmax(logits, dim=1)  # pylint: disable = (no-member)
        self.test_accuracy.update(preds, targets)  # pylint: disable = (no-member)

        # Calling self.log will surface up scalars for you in TensorBoard
        self.log("test_loss", loss, prog_bar=True)
        self.log("test_acc", self.test_accuracy, prog_bar=True)

    def configure_optimizers(self) -> torch.optim.Optimizer:
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        return optimizer

    def train_dataloader(self) -> DataLoader:
        return self.dataloader_train

    def test_dataloader(self) -> DataLoader:
        return self.dataloader_test

    def val_dataloader(self) -> DataLoader:
        return self.dataloader_val

@step(enable_cache=True)
def trainer(
    dataloader_train: DataLoader,
    dataloader_test: DataLoader,
    dataloader_val: DataLoader,
) -> nn.Module:
    """Trains on the train dataloader."""
    pretrained_model, categories, _ = load_model()

    # uncomment if you want to re-train model
    custom_model = CustomModel(
        model=pretrained_model,
        num_labels=len(categories),
        dataloader_train=dataloader_train,
        dataloader_test=dataloader_test,
        dataloader_val=dataloader_val,
    )

    trainer = Trainer(
        accelerator="auto",
        devices=[0],
        max_epochs=3,
        val_check_interval=1.0,
    )
    trainer.fit(custom_model)
    trainer.test(custom_model)
    return trainer.model.model
