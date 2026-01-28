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
"""Data loader step for Run:AI example."""

from typing import Tuple

import numpy as np

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def data_loader() -> Tuple[np.ndarray, np.ndarray]:
    """Load synthetic data for demonstration.

    Creates a simple synthetic dataset for demonstration purposes.
    Returns simple numpy arrays (no PyTorch/TensorFlow dependencies).

    Returns:
        Tuple of (X_train, y_train) as numpy arrays
    """
    logger.info("🔄 Generating synthetic data...")

    # Set random seed for reproducibility
    np.random.seed(42)

    # Generate synthetic data
    num_samples = 1000
    num_features = 20

    # Create random features
    X = np.random.randn(num_samples, num_features).astype(np.float32)

    # Create labels (simple linear separation with noise)
    weights = np.random.randn(num_features)
    y = (X @ weights + np.random.randn(num_samples) * 0.1 > 0).astype(
        np.float32
    )

    logger.info(f"  Total samples: {num_samples}")
    logger.info(f"  Features: {num_features}")
    logger.info(f"  Class distribution: {np.bincount(y.astype(int)).tolist()}")

    logger.info("✅ Data loaded successfully")

    return X, y
