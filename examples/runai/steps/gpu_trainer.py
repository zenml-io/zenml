#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""GPU trainer step for Run:AI step operator example."""

from typing import Any, Dict, Tuple

import numpy as np

from zenml import step
from zenml.config import DockerSettings, PythonPackageInstaller
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions
from zenml.integrations.runai.flavors.runai_step_operator_flavor import (
    RunAIStepOperatorSettings,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

# Custom PyTorch GPU image with ZenML pre-installed
gpu_docker_settings = DockerSettings(
    parent_image="safoinext/zenml:runai-pytorch-25.02",
    build_config=DockerBuildConfig(
        build_options=DockerBuildOptions(platform="linux/amd64"),
    ),
    python_package_installer=PythonPackageInstaller.PIP,
)

# Run:AI step operator settings showcasing multiple features
runai_settings = RunAIStepOperatorSettings(
    # GPU allocation - request 1 full GPU using portion (1.0 = 100%)
    gpu_portion_request=1.0,
    gpu_request_type="portion",
    # Reduced CPU resources to improve schedulability
    cpu_core_request=1.0,
    cpu_core_limit=2.0,
    cpu_memory_request="2Gi",
    cpu_memory_limit="4Gi",
    # Scheduling preferences
    preemptibility="non-preemptible",
    # PyTorch DataLoader compatibility
    large_shm_request=True,
    # Execution control
    backoff_limit=2,
    termination_grace_period_seconds=60,
    # Environment variables
    environment_variables={
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
    },
)


@step(
    step_operator="runai",
    settings={
        "step_operator": runai_settings,
        "docker": gpu_docker_settings,
    },
    enable_cache=False,
)
def gpu_trainer(data: Tuple[np.ndarray, np.ndarray]) -> Dict[str, Any]:
    """Train a simple model on GPU via Run:AI step operator.

    This step demonstrates:
    - Offloading to Run:AI with fractional GPU (0.5 GPU)
    - Custom PyTorch GPU image
    - Various step operator settings (preemptibility, labels, etc.)

    Args:
        data: Tuple of (X, y) training data as numpy arrays.

    Returns:
        Dictionary containing training metrics and GPU info.
    """
    import torch
    import torch.nn as nn

    X, y = data

    logger.info("Starting GPU training step...")
    
    # Detailed CUDA diagnostics
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    logger.info(f"CUDA version: {torch.version.cuda}")
    logger.info(f"cuDNN version: {torch.backends.cudnn.version()}")
    logger.info(f"Number of GPUs: {torch.cuda.device_count()}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(
            f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB"
        )
    else:
        logger.warning(
            "CUDA not available! This could be due to:\n"
            "  1. Running on a cluster with simulated/fake GPUs (run.ai/fake.gpu=true)\n"
            "  2. GPU not allocated by Run:AI scheduler\n"
            "  3. NVIDIA drivers not installed/compatible\n"
            "Check Run:AI workload logs and node labels with kubectl."
        )

    # Convert to tensors and move to GPU
    X_tensor = torch.tensor(X, dtype=torch.float32).to(device)
    y_tensor = torch.tensor(y, dtype=torch.float32).to(device)

    # Simple model
    model = nn.Sequential(
        nn.Linear(X.shape[1], 64),
        nn.ReLU(),
        nn.Linear(64, 1),
        nn.Sigmoid(),
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.BCELoss()

    # Training loop
    logger.info("Training for 100 epochs...")
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X_tensor).squeeze()
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 25 == 0:
            logger.info(f"Epoch {epoch + 1}/100, Loss: {loss.item():.4f}")

    # Evaluate
    with torch.no_grad():
        predictions = (model(X_tensor).squeeze() > 0.5).float()
        accuracy = (predictions == y_tensor).float().mean().item()

    logger.info(f"Training complete! Accuracy: {accuracy:.2%}")

    return {
        "final_loss": loss.item(),
        "accuracy": accuracy,
        "device": str(device),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None
        ),
    }


