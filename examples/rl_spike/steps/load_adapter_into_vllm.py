"""Hot-load a ZenML LoRA adapter artifact into the warm vLLM server."""

import time
from typing import Any, Dict

from serving import load_lora_adapter
from zenml import log_metadata, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact


@step(enable_cache=False)
def load_adapter_into_vllm(
    adapter: UnmaterializedArtifact,
    endpoint: Dict[str, Any],
    adapter_name: str,
) -> Dict[str, Any]:
    """Materialize and hot-load one ZenML adapter artifact into vLLM.

    The adapter remains modeled as a ZenML artifact. This step reads its
    artifact URI, copies the `PathMaterializer` archive into the running
    vLLM pod, extracts it to a local LoRA directory, and tells vLLM to load
    that directory under a versioned adapter name.

    Args:
        adapter: Unmaterialized ZenML artifact returned by init_lora or
            grpo_update.
        endpoint: Endpoint record returned by ensure_vllm_server.
        adapter_name: Versioned LoRA name to request during rollouts.

    Returns:
        Adapter serving record consumed by generate_rollouts_from_endpoint.
    """
    started = time.time()
    loaded = load_lora_adapter(
        endpoint=endpoint,
        adapter_uri=adapter.uri,
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
