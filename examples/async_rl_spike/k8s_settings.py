"""Remote-serving (Kubernetes) settings for the async RL spike.

Remote mode gives every published version its own raw Kubernetes vLLM
Deployment and Service. The per-version names are the prefixes below plus
"-v{version}". See the rl_spike example's GPU_SETUP.md for how the server
image and namespace are provisioned.
"""

from typing import Any, Dict

ECR = "339712793861.dkr.ecr.eu-central-1.amazonaws.com"

VLLM_SERVER_IMAGE = f"{ECR}/zenml-rl-spike-vllm-server:0.2"
VLLM_NAMESPACE = "michael"
VLLM_DEPLOYMENT_PREFIX = "async-rl-spike-vllm"
VLLM_SERVICE_PREFIX = "async-rl-spike-vllm"
VLLM_SERVICE_ACCOUNT_NAME = "zenml-service-account"


def remote_deploy_config(
    image: str = VLLM_SERVER_IMAGE,
    namespace: str = VLLM_NAMESPACE,
    deployment_prefix: str = VLLM_DEPLOYMENT_PREFIX,
    service_prefix: str = VLLM_SERVICE_PREFIX,
    service_account_name: str = VLLM_SERVICE_ACCOUNT_NAME,
    max_lora_rank: int = 32,
) -> Dict[str, Any]:
    """Build the deploy_config the trainer uses in remote mode.

    Args:
        image: vLLM server image.
        namespace: Kubernetes namespace.
        deployment_prefix: Per-version Deployment name prefix.
        service_prefix: Per-version Service name prefix.
        service_account_name: Kubernetes service account for the pods.
        max_lora_rank: Maximum LoRA rank accepted by vLLM.

    Returns:
        Deployment settings dict.
    """
    return {
        "backend": "k8s",
        "image": image,
        "namespace": namespace,
        "deployment_prefix": deployment_prefix,
        "service_prefix": service_prefix,
        "service_account_name": service_account_name,
        "max_lora_rank": max_lora_rank,
    }
