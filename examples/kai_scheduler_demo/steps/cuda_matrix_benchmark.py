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
"""CUDA matrix multiplication benchmark step."""

import subprocess
from typing import Dict

import torch

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


def _log_nvidia_smi() -> None:
    """Run nvidia-smi and log the output for GPU visibility during demos."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("nvidia-smi output:\n%s", result.stdout)
        else:
            logger.warning("nvidia-smi failed: %s", result.stderr)
    except FileNotFoundError:
        logger.warning("nvidia-smi not found on this node.")
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out.")

_WARMUP_ITERATIONS = 3


def _cleanup_gpu() -> None:
    """Free GPU memory caches if CUDA is available."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


@step
def cuda_matrix_benchmark(matrix_size: int = 4096) -> Dict[str, float]:
    """Benchmark GPU throughput via CUDA matrix multiplication.

    Allocates two square matrices on the GPU, performs a timed matrix multiply,
    and reports GFLOPS. Runs a short warmup first to avoid cold-start bias.
    Falls back gracefully to CPU when no GPU is present.

    Args:
        matrix_size: Edge length of the square matrices (N×N). Larger values
            stress memory bandwidth more than pure compute.

    Returns:
        Dict with benchmark results: elapsed_ms, gflops, device, memory_mb.
    """
    _log_nvidia_smi()

    device_name = "cpu"
    device = torch.device("cpu")

    if torch.cuda.is_available():
        device = torch.device("cuda")
        device_name = torch.cuda.get_device_name(0)
        logger.info("GPU detected: %s", device_name)
        logger.info(
            "GPU memory: %.1f GiB total / %.1f GiB free",
            torch.cuda.get_device_properties(0).total_memory / 1024**3,
            torch.cuda.memory_reserved(0) / 1024**3,
        )
    else:
        logger.warning(
            "No CUDA GPU found — running benchmark on CPU. "
            "Performance will be significantly lower."
        )

    try:
        a = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)
        b = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)

        # Warmup so CUDA JIT and caching don't skew the timed run.
        for _ in range(_WARMUP_ITERATIONS):
            _ = torch.mm(a, b)
        if device.type == "cuda":
            torch.cuda.synchronize()

        start_event = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
        end_event = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None

        import time

        t0 = time.perf_counter()
        if start_event:
            start_event.record()

        result = torch.mm(a, b)

        if end_event:
            end_event.record()
            torch.cuda.synchronize()
            elapsed_ms = start_event.elapsed_time(end_event)  # type: ignore[union-attr]
        else:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # FLOPs for matrix multiply: 2 * N^3
        flops = 2.0 * matrix_size**3
        gflops = flops / (elapsed_ms / 1000.0) / 1e9

        memory_mb = (
            torch.cuda.memory_allocated(0) / 1024**2
            if device.type == "cuda"
            else 0.0
        )

        logger.info(
            "Benchmark complete — %.1f ms, %.1f GFLOPS (matrix %dx%d on %s)",
            elapsed_ms,
            gflops,
            matrix_size,
            matrix_size,
            device_name,
        )
        del result, a, b

        metrics = {
            "elapsed_ms": elapsed_ms,
            "gflops": gflops,
            "memory_mb": memory_mb,
            "matrix_size": float(matrix_size),
        }
        log_metadata(
            metadata={
                "benchmark": {
                    "device": device_name,
                    "matrix_size": matrix_size,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "gflops": round(gflops, 2),
                    "memory_allocated_mb": round(memory_mb, 2),
                }
            }
        )
        return metrics

    finally:
        _cleanup_gpu()
