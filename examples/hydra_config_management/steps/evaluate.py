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
"""Evaluation step for the Hydra config management example."""

from typing import Annotated, Any, Dict

import torch
from lightning import LightningModule, Trainer

from steps.data import get_fashion_mnist_loaders
from zenml import log_metadata, step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            memory="2GB",
        )
    }
)
def evaluate_model(
    model: LightningModule,
    batch_size: int = 64,
) -> Annotated[Dict[str, Any], "evaluation_results"]:
    """Evaluate a trained model on the FashionMNIST validation set.

    Runs the model through the validation set and reports per-class
    accuracy alongside the overall metrics.

    Args:
        model: Trained Lightning model to evaluate
        batch_size: Batch size for data loading

    Returns:
        Dictionary with val_loss, val_accuracy, and per-class accuracy
    """
    print("\n📊 Evaluating trained model")

    _, val_loader = get_fashion_mnist_loaders(batch_size=batch_size)
    print(f"   Validation samples: {len(val_loader.dataset)}")

    trainer = Trainer(
        accelerator="auto",
        devices=1,
        enable_progress_bar=False,
        logger=False,
    )

    results = trainer.validate(model, val_loader, verbose=False)
    val_loss = results[0].get("val_loss", 0.0)
    val_accuracy = results[0].get("val_acc", 0.0) * 100

    class_names = [
        "T-shirt/top",
        "Trouser",
        "Pullover",
        "Dress",
        "Coat",
        "Sandal",
        "Shirt",
        "Sneaker",
        "Bag",
        "Ankle boot",
    ]

    model.eval()
    class_correct = [0] * 10
    class_total = [0] * 10

    with torch.no_grad():
        for batch in val_loader:
            images, labels = batch
            outputs = model(images)
            predictions = outputs.argmax(dim=1)

            for label, prediction in zip(labels, predictions):
                class_total[label.item()] += 1
                if label == prediction:
                    class_correct[label.item()] += 1

    print(f"\n   Overall: loss={val_loss:.4f}, accuracy={val_accuracy:.2f}%")
    print("\n   Per-class accuracy:")

    per_class_accuracy = {}
    for i, name in enumerate(class_names):
        if class_total[i] > 0:
            acc = 100.0 * class_correct[i] / class_total[i]
        else:
            acc = 0.0
        per_class_accuracy[name] = acc
        print(f"      {name:>15s}: {acc:.1f}%")

    print("✅ Evaluation complete\n")

    evaluation = {
        "val_loss": val_loss,
        "val_accuracy": val_accuracy,
        "per_class_accuracy": per_class_accuracy,
    }

    log_metadata(
        metadata={
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "per_class_accuracy": per_class_accuracy,
        },
        infer_artifact=True,
    )

    return evaluation
