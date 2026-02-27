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
"""Test step: evaluate the trained model on test data and log test metrics."""

import base64
import io
import random
from typing import Annotated, Any, Dict

import matplotlib.pyplot as plt
import numpy as np
import torch
from lightning import LightningModule

from steps.dataloader import get_dataloader
from steps.utils import N_SAMPLE_IMAGES, plot_sample_predictions
from zenml import log_metadata, step
from zenml.types import HTMLString


def _load_model(path: str) -> LightningModule:
    """Load a LightningModule from a path on the PVC (saved with torch.save)."""
    return torch.load(path, map_location="cpu", weights_only=False)


def _evaluate_model(
    model: LightningModule, test_loader: Any
) -> Dict[str, float]:
    """Run model on test_loader and return test loss and accuracy (%)."""
    model.eval()
    loss_fn = getattr(model, "loss_fn", torch.nn.CrossEntropyLoss())
    total_loss = 0.0
    total_correct = 0
    total = 0
    with torch.no_grad():
        for batch in test_loader:
            x, y = batch
            if next(model.parameters()).is_cuda:
                x, y = x.cuda(), y.cuda()
            logits = model(x)
            loss = loss_fn(logits, y)
            total_loss += loss.item() * x.size(0)
            total_correct += (logits.argmax(1) == y).sum().item()
            total += x.size(0)
    return {
        "test_loss": total_loss / total if total else 0.0,
        "test_accuracy": 100.0 * total_correct / total if total else 0.0,
    }


@step
def test_model(
    trained_model_path: str,
    preprocessed_paths: Dict[str, str],
    seed: int,
) -> Annotated[HTMLString, "sample_predictions_visualization"]:
    """Evaluate the trained model on the test set and log metrics.

    Test result is printed and logged as metadata only (not returned).
    Returns a sample predictions plot as HTML for ZenML dashboard visualization.
    The model is not returned (already saved in the train step).

    Args:
        trained_model_path: Path to the saved model file on PVC (e.g. .../models/model/model.pt).
        preprocessed_paths: Dict with "test" key pointing to test data directory path.
        seed: Random seed for reproducibility.

    Returns:
        HTML visualization of 6 randomly selected test predictions.
    """
    print("\nTesting model on test set")
    random.seed(seed)
    model = _load_model(trained_model_path)

    test_loader = get_dataloader(
        preprocessed_paths["test"], batch_size=256, shuffle=False
    )
    n_test = len(test_loader.dataset)  # type: ignore[arg-type]

    metrics = _evaluate_model(model, test_loader)
    test_result = {
        "n_test_samples": n_test,
        "test_loss": metrics["test_loss"],
        "test_accuracy": metrics["test_accuracy"],
    }

    print("  Test result")
    print("  ----------")
    print(f"    test_loss:     {metrics['test_loss']:.4f}")
    print(f"    test_accuracy: {metrics['test_accuracy']:.2f}%")
    print(f"    n_test_samples: {n_test}")
    print("  Test step complete\n")

    log_metadata(metadata=test_result)  # type: ignore[arg-type]

    # Randomly select 6 test samples for the visualization
    dataset = test_loader.dataset
    n_sample = min(N_SAMPLE_IMAGES, n_test)
    indices = random.sample(range(n_test), n_sample)
    images_list = []
    actual_list = []
    for idx in indices:
        x, y = dataset[idx]
        images_list.append(x.numpy())
        actual_list.append(y)
    images_np = np.stack(images_list, axis=0)
    actual_np = np.array(actual_list, dtype=np.int64)
    model.eval()
    with torch.no_grad():
        batch = torch.from_numpy(images_np)
        logits = model(batch)
        pred_np = logits.argmax(1).cpu().numpy()

    fig = plot_sample_predictions(images_np, actual_np, pred_np)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    html = f'<div style="text-align: center;"><img src="data:image/png;base64,{image_base64}" style="max-width: 100%; height: auto;"></div>'
    return HTMLString(html)
