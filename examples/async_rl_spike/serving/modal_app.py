"""Deployable Modal app: one warm vLLM server with runtime LoRA loading.

Deploy once, then the trainer loads/unloads a LoRA per version into it:

    modal deploy serving/modal_app.py

The model, GPU, and max LoRA rank are baked in at deploy time via env vars
(ASYNC_RL_MODEL, ASYNC_RL_GPU, ASYNC_RL_MAX_LORA_RANK).

Adapters arrive on a Modal Volume that the trainer writes to from outside.
A running container does not see external Volume writes until it reloads, so
a background thread reloads the adapters Volume on an interval. The trainer
then calls vLLM's `/v1/load_lora_adapter` and retries until the reloaded
file is visible.
"""

import os
import subprocess
import threading
import time

import modal

MODEL = os.environ.get("ASYNC_RL_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
GPU = os.environ.get("ASYNC_RL_GPU", "L4")
MAX_LORA_RANK = int(os.environ.get("ASYNC_RL_MAX_LORA_RANK", "32"))
GPU_MEMORY_UTILIZATION = os.environ.get("ASYNC_RL_GPU_MEM_UTIL", "0.80")
APP_NAME = os.environ.get("ASYNC_RL_MODAL_APP", "async-rl-spike-vllm")
ADAPTERS_VOLUME = os.environ.get(
    "ASYNC_RL_MODAL_ADAPTERS_VOLUME", "async-rl-spike-adapters"
)

VLLM_PORT = 8000
ADAPTER_ROOT = "/adapters"
RELOAD_INTERVAL_SECONDS = 5
MINUTES = 60

vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12"
    )
    .pip_install("vllm==0.24.0", "huggingface_hub[hf_transfer]")
    .env(
        {
            "VLLM_ALLOW_RUNTIME_LORA_UPDATING": "1",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
)

hf_cache = modal.Volume.from_name(
    "async-rl-spike-hf-cache", create_if_missing=True
)
vllm_cache = modal.Volume.from_name(
    "async-rl-spike-vllm-cache", create_if_missing=True
)
adapters = modal.Volume.from_name(ADAPTERS_VOLUME, create_if_missing=True)

app = modal.App(APP_NAME)


@app.function(
    image=vllm_image,
    gpu=GPU,
    volumes={
        ADAPTER_ROOT: adapters,
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
    },
    min_containers=1,
    max_containers=1,
    scaledown_window=15 * MINUTES,
    timeout=24 * 60 * MINUTES,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve() -> None:
    """Start vLLM and keep the adapters Volume fresh for runtime loading."""

    def _reload_loop() -> None:
        while True:
            try:
                adapters.reload()
            except Exception:
                pass
            time.sleep(RELOAD_INTERVAL_SECONDS)

    threading.Thread(target=_reload_loop, daemon=True).start()
    subprocess.Popen(
        [
            "vllm",
            "serve",
            MODEL,
            "--enable-lora",
            "--max-lora-rank",
            str(MAX_LORA_RANK),
            "--max-model-len",
            "8192",
            # T4-class GPUs OOM under vLLM's CUDA-graph capture and default
            # memory reservation, so run eager and leave GPU headroom.
            "--enforce-eager",
            "--gpu-memory-utilization",
            GPU_MEMORY_UTILIZATION,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
        ]
    )
