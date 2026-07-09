"""Minimal full-remote check on the Modal stack (lightweight orchestration).

One step, orchestrated by the Modal orchestrator in a light container (no
torch). It validates the pieces the real run depends on: authenticating to
Modal from inside an orchestrated container with the stack's Modal secret,
resolving the deployed vLLM app, and generating over HTTP.

    modal deploy serving/modal_app.py     # once, if not already deployed
    python minimal_remote.py
"""

from typing import Any, Dict

from zenml import log_metadata, pipeline, step
from zenml.config import DockerSettings

MODEL = "Qwen/Qwen3-0.6B"
APP_NAME = "async-rl-spike-vllm"

DOCKER = DockerSettings(requirements=["modal>=0.64"])


@step
def remote_serving_check(model_name: str, app_name: str) -> Dict[str, Any]:
    """Resolve the app via the Modal secret and generate over HTTP.

    Args:
        model_name: HF model ID served by the Modal app.
        app_name: Deployed Modal app name.

    Returns:
        Summary with the resolved URL and a sample completion.
    """
    from serving.modal_vllm import ensure_modal_deployment, modal_deploy_config
    from serving.vllm_http import completion_text, post_chat_completions

    deploy_config = modal_deploy_config(app_name=app_name)
    endpoint = ensure_modal_deployment(
        model_name=model_name, deploy_config=deploy_config
    )
    choices = post_chat_completions(
        endpoint_url=endpoint["url"],
        adapter_name=model_name,
        messages=[{"role": "user", "content": "Say hello in three words."}],
        group_size=1,
        temperature=0.7,
        max_tokens=32,
    )
    result = {
        "web_url": endpoint["url"],
        "sample_completion": completion_text(choices[0])[:200],
    }
    log_metadata(metadata=result)
    return result


@pipeline(enable_cache=False, settings={"docker": DOCKER})
def minimal_remote(model_name: str = MODEL, app_name: str = APP_NAME) -> None:
    """Run the remote serving check on the Modal orchestrator."""
    remote_serving_check(model_name=model_name, app_name=app_name)


if __name__ == "__main__":
    minimal_remote()
