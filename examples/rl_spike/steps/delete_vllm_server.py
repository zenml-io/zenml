"""Delete the warm vLLM server after a successful warm-mode run."""

import time
from typing import Any, Dict

from serving import delete_vllm_deployment

from zenml import log_metadata, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact


@step(enable_cache=False)
def delete_vllm_server(
    endpoint: Dict[str, Any], final_adapter: UnmaterializedArtifact
) -> None:
    """Delete the raw Kubernetes vLLM Deployment and Service.

    This is a best-effort normal-completion cleanup step. If the pipeline is
    killed before this step runs, the manual scale-down instructions in
    GPU_SETUP.md still apply. The final_adapter argument is intentionally
    unused; it gives ZenML a data dependency so cleanup cannot run before
    the last training step produced the final adapter artifact.

    Args:
        endpoint: Endpoint record returned by ensure_vllm_server.
        final_adapter: Final adapter artifact from grpo_update.
    """
    _ = final_adapter
    started = time.time()
    delete_vllm_deployment(endpoint=endpoint)
    log_metadata(
        metadata={
            "vllm.deleted_deployment_name": endpoint["deployment_name"],
            "vllm.deleted_service_name": endpoint["service_name"],
            "vllm.delete_seconds": round(time.time() - started, 2),
        }
    )
