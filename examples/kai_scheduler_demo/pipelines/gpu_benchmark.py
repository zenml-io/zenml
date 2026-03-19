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
"""GPU benchmark pipeline: CUDA matmul → PyTorch CNN training."""

from zenml import pipeline

from steps import cuda_matrix_benchmark, pytorch_cnn_train


@pipeline(name="kai_gpu_benchmark")
def kai_gpu_benchmark_pipeline(
    matrix_size: int = 4096,
    epochs: int = 5,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
) -> None:
    """Two-step GPU pipeline showcasing ZenML + KAI-Scheduler integration.

    Step 1 — `cuda_matrix_benchmark`:
        Runs a CUDA matrix multiplication benchmark and reports GFLOPS.
        Demonstrates that KAI-Scheduler correctly places the pod on a GPU
        node from the configured queue.

    Step 2 — `pytorch_cnn_train`:
        Trains a minimal CNN on synthetic image data for the given number of
        epochs. Logs per-epoch loss to ZenML metadata.

    Both steps use the KAI-Scheduler (when configured) via the
    `orchestrator.kubernetes` settings in the YAML config, which sets
    `schedulerName`, queue label, GPU resource requests, and optional
    gang-scheduling PodGroup.

    Args:
        matrix_size: Edge length (N) for the N×N benchmark matrices.
        epochs: Training epochs for the CNN step.
        batch_size: Mini-batch size for training.
        learning_rate: Adam optimizer learning rate.
    """
    benchmark_result = cuda_matrix_benchmark(matrix_size=matrix_size)
    pytorch_cnn_train(
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        after=[benchmark_result],
    )
