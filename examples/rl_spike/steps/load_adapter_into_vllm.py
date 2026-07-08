"""Hot-load a ZenML LoRA adapter artifact into the warm vLLM server."""

import time
from pathlib import Path
from typing import Any, Dict

from serving import load_lora_adapter

from zenml import get_step_context, log_metadata, step


@step(enable_cache=False)
def load_adapter_into_vllm(
    adapter: Path,
    endpoint: Dict[str, Any],
    adapter_name: str,
) -> Dict[str, Any]:
    """Hot-load one ZenML adapter artifact into the warm vLLM server.

    The adapter arrives as a *materialized* `Path` input: ZenML downloads
    the LoRA directory into this step pod using the artifact store's
    connector credentials — the canonical in-step way to read artifact
    storage. The helper then pushes those local bytes into the raw vLLM
    pod over the exec websocket and tells vLLM to load the directory
    under a versioned adapter name. The vLLM pod itself never touches S3
    (its node role has no access, and it has no ZenML session to get
    connector credentials — both verified live).

    Args:
        adapter: Materialized LoRA adapter directory from init_lora or
            grpo_update.
        endpoint: Endpoint record returned by ensure_vllm_server.
        adapter_name: Versioned LoRA name to request during rollouts.

    Returns:
        Adapter serving record consumed by generate_rollouts_from_endpoint.
    """
    started = time.time()
    inputs = get_step_context().inputs.get("adapter")
    adapter_uri = inputs[0].uri if inputs else "unknown"
    loaded = load_lora_adapter(
        endpoint=endpoint,
        adapter_dir=str(adapter),
        adapter_uri=adapter_uri,
        adapter_name=adapter_name,
    )
    log_metadata(
        metadata={
            "vllm.loaded_adapter_name": loaded["adapter_name"],
            "vllm.loaded_adapter_uri": loaded["adapter_uri"],
            "vllm.loaded_adapter_path": loaded["adapter_path"],
            "vllm.load_adapter_seconds": round(time.time() - started, 2),
        }
    )
    return loaded
