"""Modal serving backend: drive the deployed vLLM app from the trainer.

The Modal app (serving/modal_app.py) is deployed once and serves the base
model with runtime LoRA loading. These helpers give it the same
ensure/load/teardown contract as the Kubernetes backend, so
steps.disaggregated can dispatch on deploy_config["backend"]. A version is a
loaded LoRA on the one shared app, so retirement unloads the adapter rather
than deleting a deployment.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict


def modal_deploy_config(
    app_name: str = "async-rl-spike-vllm",
    adapters_volume: str = "async-rl-spike-adapters",
    max_lora_rank: int = 32,
) -> Dict[str, Any]:
    """Build the deploy_config for the Modal backend.

    Args:
        app_name: Deployed Modal app name (matches modal_app.py).
        adapters_volume: Modal Volume the trainer writes adapters to.
        max_lora_rank: Maximum LoRA rank the app was deployed with.

    Returns:
        Deployment settings dict tagged with backend "modal".
    """
    return {
        "backend": "modal",
        "app_name": app_name,
        "adapters_volume": adapters_volume,
        "max_lora_rank": max_lora_rank,
    }


def _modal_client_and_env() -> Any:
    """Build a Modal client from the active stack's Modal component creds."""
    from zenml.client import Client
    from zenml.integrations.modal.sandbox_utils import (
        create_modal_client_from_credentials,
    )

    stack = Client().active_stack
    for component in (stack.sandbox, stack.orchestrator, stack.step_operator):
        config = getattr(component, "config", None)
        token_id = getattr(config, "token_id", None)
        token_secret = getattr(config, "token_secret", None)
        if token_id and token_secret:
            client = create_modal_client_from_credentials(
                token_id=token_id, token_secret=token_secret
            )
            return client, getattr(config, "modal_environment", None)
    return None, None


def _modal_web_url(app_name: str) -> str:
    """Resolve the deployed vLLM app's web URL, or fail with guidance.

    Args:
        app_name: Deployed Modal app name.

    Raises:
        RuntimeError: If the URL cannot be resolved from the SDK.

    Returns:
        The `serve` function's public HTTPS URL.
    """
    override = os.environ.get("ASYNC_RL_MODAL_URL")
    if override:
        return override

    import modal

    client, environment = _modal_client_and_env()
    fn = modal.Function.from_name(
        app_name, "serve", environment_name=environment, client=client
    )
    getter = getattr(fn, "get_web_url", None)
    url = getter() if callable(getter) else getattr(fn, "web_url", None)
    if not url:
        raise RuntimeError(
            f"Could not resolve the Modal web URL for app {app_name!r}. "
            "Deploy it with `modal deploy serving/modal_app.py`, or set "
            "ASYNC_RL_MODAL_URL to the serve endpoint."
        )
    return url


def _wait_for_http_health(endpoint_url: str, timeout_seconds: int) -> None:
    """Wait until the vLLM server answers its health endpoint.

    Args:
        endpoint_url: Base URL of the vLLM server.
        timeout_seconds: Readiness timeout.

    Raises:
        TimeoutError: If the server does not answer in time.
    """
    deadline = time.time() + timeout_seconds
    health_url = f"{endpoint_url.rstrip('/')}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=10) as response:
                if 200 <= response.status < 300:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(5)
    raise TimeoutError(
        f"Modal vLLM endpoint {endpoint_url!r} did not answer "
        f"{health_url!r} within {timeout_seconds}s."
    )


def ensure_modal_deployment(
    *,
    model_name: str,
    deploy_config: Dict[str, Any],
    timeout_seconds: int = 900,
) -> Dict[str, Any]:
    """Resolve the deployed Modal app's endpoint and wait until it is ready.

    Args:
        model_name: HF model ID the app serves (recorded for lineage).
        deploy_config: Modal deployment settings.
        timeout_seconds: Readiness timeout.

    Returns:
        Endpoint record shared by all versions (one app, many adapters).
    """
    url = _modal_web_url(deploy_config["app_name"])
    _wait_for_http_health(url, timeout_seconds=timeout_seconds)
    return {
        "url": url,
        "backend": "modal",
        "app_name": deploy_config["app_name"],
        "adapters_volume": deploy_config["adapters_volume"],
        "model_name": model_name,
    }


def _post(url: str, payload: Dict[str, Any], timeout: int = 60) -> int:
    """POST JSON and return the HTTP status code."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code


def load_lora_adapter_modal(
    *,
    endpoint: Dict[str, Any],
    adapter_dir: str,
    adapter_name: str,
    deploy_config: Dict[str, Any],
    attempts: int = 12,
    retry_interval_seconds: int = 5,
) -> Dict[str, Any]:
    """Upload a version's adapter to the Volume and hot-load it into vLLM.

    Retries the load because the app sees the freshly uploaded adapter only
    after its next Volume reload (see modal_app.py).

    Args:
        endpoint: Endpoint record from ensure_modal_deployment.
        adapter_dir: Local adapter directory to upload.
        adapter_name: LoRA name used in rollout requests.
        deploy_config: Modal deployment settings.
        attempts: How many times to retry the load.
        retry_interval_seconds: Delay between load attempts.

    Raises:
        RuntimeError: If vLLM never loads the adapter.

    Returns:
        Record with the loaded adapter name and in-app path.
    """
    import modal

    client, environment = _modal_client_and_env()
    volume = modal.Volume.from_name(
        deploy_config["adapters_volume"],
        environment_name=environment,
        create_if_missing=True,
        client=client,
    )
    with volume.batch_upload(force=True) as batch:
        batch.put_directory(adapter_dir, f"/{adapter_name}")

    lora_path = f"/adapters/{adapter_name}"
    load_url = f"{endpoint['url'].rstrip('/')}/v1/load_lora_adapter"
    payload = {"lora_name": adapter_name, "lora_path": lora_path}
    for _ in range(attempts):
        if _post(load_url, payload) < 300:
            return {
                "adapter_name": adapter_name,
                "adapter_path": lora_path,
                "endpoint_url": endpoint["url"],
            }
        time.sleep(retry_interval_seconds)
    raise RuntimeError(
        f"vLLM did not load adapter {adapter_name!r} from {lora_path} after "
        f"{attempts} attempts."
    )


def unload_lora_adapter_modal(
    *, endpoint: Dict[str, Any], adapter_name: str
) -> None:
    """Unload a retired version's adapter from the shared vLLM app.

    Args:
        endpoint: Endpoint record for the version.
        adapter_name: LoRA name to unload.
    """
    unload_url = f"{endpoint['url'].rstrip('/')}/v1/unload_lora_adapter"
    try:
        _post(unload_url, {"lora_name": adapter_name})
    except urllib.error.URLError:
        pass
