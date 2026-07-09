"""Serving helpers for the async RL spike remote mode."""

from serving.k8s_vllm import (
    DEFAULT_VLLM_PORT,
    delete_vllm_deployment,
    ensure_vllm_deployment,
    load_lora_adapter,
)
from serving.vllm_http import (
    VLLMEndpointError,
    completion_text,
    extract_ids_and_logprobs,
    post_chat_completions,
)

__all__ = [
    "DEFAULT_VLLM_PORT",
    "VLLMEndpointError",
    "completion_text",
    "delete_vllm_deployment",
    "ensure_vllm_deployment",
    "extract_ids_and_logprobs",
    "load_lora_adapter",
    "post_chat_completions",
]
