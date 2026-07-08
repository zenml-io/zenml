"""Per-iteration rollout generation through a warm vLLM server."""

import time
from typing import Any, Dict, List

from serving.vllm_http import generate_vllm_chat_completions
from zenml import log_metadata, step


@step(enable_cache=False)
def generate_rollouts_from_endpoint(
    tasks: List[Dict[str, Any]],
    endpoint: Dict[str, Any],
    loaded_adapter: Dict[str, Any],
    group_size: int,
    model_name: str,
    temperature: float = 0.9,
    max_tokens: int = 1024,
) -> List[Dict[str, Any]]:
    """Generate rollout seeds by calling the warm vLLM HTTP endpoint.

    Args:
        tasks: Task records.
        endpoint: Endpoint record from ensure_vllm_server.
        loaded_adapter: Adapter record from load_adapter_into_vllm.
        group_size: GRPO group size.
        model_name: HF model ID; used for tokenizer IDs.
        temperature: Sampling temperature.
        max_tokens: Generation cap.

    Returns:
        One episode dict per (task, rollout_index), ready for run_episode.map.
    """
    started = time.time()
    episodes = generate_vllm_chat_completions(
        endpoint_url=endpoint["url"],
        model_name=model_name,
        adapter_name=loaded_adapter["adapter_name"],
        tasks=tasks,
        group_size=group_size,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    completion_tokens = sum(len(e["completion_ids"]) for e in episodes)
    log_metadata(
        metadata={
            "generation_mode": "warm_vllm_http",
            "vllm.endpoint_url": endpoint["url"],
            "vllm.adapter_name": loaded_adapter["adapter_name"],
            "generation_seconds": round(time.time() - started, 2),
            "num_episodes": len(episodes),
            "completion_tokens": completion_tokens,
        }
    )
    return episodes
