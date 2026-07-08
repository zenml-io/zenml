"""Smallest possible GPU pipeline: one step that proves CUDA works.

Part of the GPU_SETUP.md smoke sequence (step 3). Run it against the
remote stack:

    zenml stack set kubernetes_aws
    python gpu_smoke.py

It uses exactly the same Docker settings and GPU pod placement as the
real RL pipeline, so a green run here also validates the image build,
ECR push, node selectors, tolerations, and the NVIDIA device plugin —
everything except vLLM and the sandbox.
"""

import subprocess

from k8s_settings import (
    DOCKER_SETTINGS,
    GPU_STEP_SETTINGS,
    ORCHESTRATOR_ON_GPU_NODE,
)

from zenml import pipeline, step
from zenml.enums import StepRuntime


@step(runtime=StepRuntime.ISOLATED, settings=GPU_STEP_SETTINGS)
def gpu_check() -> str:
    """Print and return nvidia-smi output + what torch sees.

    Returns:
        Human-readable GPU report (also stored as the step's output
        artifact so it's inspectable in the dashboard).

    Raises:
        RuntimeError: If torch cannot see a CUDA device — a green run
            must mean the GPU actually works.
    """
    import torch

    lines = [
        f"torch {torch.__version__}",
        f"cuda available: {torch.cuda.is_available()}",
    ]
    if not torch.cuda.is_available():
        raise RuntimeError(
            "torch.cuda.is_available() is False — the pod did not get a "
            "GPU. Check node group scaling, taints, and resources."
        )
    lines.append(f"device: {torch.cuda.get_device_name(0)}")
    smi = subprocess.run(
        ["nvidia-smi"], capture_output=True, text=True, timeout=60
    )
    lines.append(smi.stdout)
    report = "\n".join(lines)
    print(report)
    return report


@pipeline(dynamic=True, enable_cache=False)
def gpu_smoke() -> None:
    """One GPU step, nothing else."""
    gpu_check()


if __name__ == "__main__":
    gpu_smoke.with_options(
        settings={
            "docker": DOCKER_SETTINGS,
            "orchestrator.kubernetes": ORCHESTRATOR_ON_GPU_NODE,
        }
    )()
