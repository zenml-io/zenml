"""Start or verify the warm vLLM rollout server."""

import time
from typing import Any, Dict

from serving import ensure_vllm_deployment
from zenml import log_metadata, step


@step(enable_cache=False)
def ensure_vllm_server(
    model_name: str,
    image: str,
    namespace: str,
    deployment_name: str,
    service_name: str,
    max_lora_rank: int = 32,
    service_account_name: str = "zenml-service-account",
) -> Dict[str, Any]:
    """Ensure the warm vLLM Kubernetes Deployment and Service exist.

    This step intentionally creates raw Kubernetes resources. ZenML records
    that the serving server was started for this run; Kubernetes keeps the
    model engine alive while rollout and training steps proceed.

    Args:
        model_name: HF model ID served as the base policy.
        image: vLLM server image.
        namespace: Kubernetes namespace.
        deployment_name: Kubernetes Deployment name.
        service_name: Kubernetes Service name.
        max_lora_rank: Maximum adapter rank accepted by vLLM.
        service_account_name: Kubernetes service account for the raw vLLM pod.

    Returns:
        Endpoint record consumed by adapter-loading and rollout steps.
    """
    started = time.time()
    endpoint = ensure_vllm_deployment(
        model_name=model_name,
        image=image,
        namespace=namespace,
        deployment_name=deployment_name,
        service_name=service_name,
        max_lora_rank=max_lora_rank,
        service_account_name=service_account_name,
    )
    log_metadata(
        metadata={
            "vllm.endpoint_url": endpoint["url"],
            "vllm.namespace": namespace,
            "vllm.deployment_name": deployment_name,
            "vllm.service_name": service_name,
            "vllm.image": image,
            "vllm.service_account_name": service_account_name,
            "vllm.ensure_seconds": round(time.time() - started, 2),
        }
    )
    return endpoint
