"""Kubernetes/GPU settings for the real (non-dry-run) pipeline.

Everything cluster-specific for the staging EKS cluster lives here, in one
place, so the pipeline code stays topology-agnostic. See GPU_SETUP.md for
how the node group, images, and namespaces referenced here get created.

Placement model on the remote stack:
- The orchestrator pod (runs the pipeline function) and the mapped
  `run_episode` steps are CPU-only and land on the default node pool.
- `init_lora`, `generate_rollouts` (vLLM batch inference), and
  `grpo_update` (TRL optimizer step) run as isolated steps on the GPU
  node (taint/label `pool=gpu`, one NVIDIA L4).
- Each `run_episode` opens a Kubernetes sandbox session pod using a
  small dedicated image that has zenml preinstalled (the sandbox flavor's
  default `python:3.11-slim` cannot run the scorer).
"""

from typing import Any, Dict, Union

from zenml.config import DockerSettings
from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.flavors import (
    KubernetesOrchestratorSettings,
    KubernetesSandboxSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

ECR = "339712793861.dkr.ecr.eu-central-1.amazonaws.com"

# Built once by hand in GPU_SETUP.md part 3; used for every sandbox
# session pod.
SANDBOX_IMAGE = f"{ECR}/zenml-rl-spike-sandbox:0.1"

# Parent image for the pipeline image: torch + CUDA + vLLM preinstalled,
# x86_64 to match the cluster nodes. ZenML layers the example's
# requirements and code on top (GPU_SETUP.md part 4).
VLLM_PARENT_IMAGE = "vllm/vllm-openai:v0.24.0-x86_64-ubuntu2404"

DOCKER_SETTINGS = DockerSettings(
    parent_image=VLLM_PARENT_IMAGE,
    requirements=[
        "trl==1.7.1",
        "peft>=0.17,<1",
        "datasets>=3.0",
    ],
    # The vLLM image has no active virtualenv, and modern uv refuses to
    # install into system Python without --system; ZenML's generated
    # `uv pip install` fails with a bare exit code 2 otherwise.
    python_package_installer_args={"system": None},
    # The cluster is x86_64; Apple Silicon laptops must cross-build.
    build_options={"platform": "linux/amd64"},
)

_GPU_POD_SETTINGS = KubernetesPodSettings(
    node_selectors={"pool": "gpu"},
    tolerations=[
        {
            "key": "pool",
            "operator": "Equal",
            "value": "gpu",
            "effect": "NoSchedule",
        }
    ],
    resources={
        "requests": {"nvidia.com/gpu": "1", "memory": "16Gi", "cpu": "4"},
        "limits": {"nvidia.com/gpu": "1", "memory": "28Gi"},
    },
)

# settings= dict for steps that need the GPU node. The keys must be
# flavor-scoped ("<component-type>.<flavor>"): ZenML's settings lookup
# only matches "type:name" or "type.flavor" keys — a bare "orchestrator"
# key validates fine but is silently never applied.
GPU_STEP_SETTINGS: Dict[str, Union[Dict[str, Any], BaseSettings]] = {
    "orchestrator.kubernetes": KubernetesOrchestratorSettings(
        pod_settings=_GPU_POD_SETTINGS
    ),
}

# settings= dict for the episode step: CPU pod, but its sandbox sessions
# need the zenml-capable image.
EPISODE_STEP_SETTINGS: Dict[str, Union[Dict[str, Any], BaseSettings]] = {
    "sandbox.kubernetes": KubernetesSandboxSettings(image=SANDBOX_IMAGE),
}
