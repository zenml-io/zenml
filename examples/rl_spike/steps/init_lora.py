"""Create the initial LoRA adapter artifact."""

import tempfile
import time
from pathlib import Path

from zenml import log_metadata, step

# Standard attention + MLP projection targets for Qwen3-family models.
LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


@step
def init_lora(model_name: str, lora_rank: int = 16) -> Path:
    """Initialize a fresh LoRA adapter for the policy model.

    The adapter directory (a few MB — adapter_model.safetensors +
    adapter_config.json, never the base weights) is the artifact that
    threads through the whole RL loop: generation loads it, grpo_update
    trains it and emits the next version.

    Args:
        model_name: HF model ID of the policy base model.
        lora_rank: LoRA rank (freshly initialized, so B=0 and the initial
            adapter is an exact no-op on the policy).

    Returns:
        Path to the saved adapter directory (archived by ZenML's
        PathMaterializer).
    """
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    started = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        model_name, dtype=torch.float32
    )
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=2 * lora_rank,
        target_modules=LORA_TARGET_MODULES,
        task_type="CAUSAL_LM",
    )
    peft_model = get_peft_model(model, lora_config)

    adapter_dir = (
        Path(tempfile.mkdtemp(prefix="rl-spike-adapter-")) / "adapter"
    )
    peft_model.save_pretrained(str(adapter_dir))

    log_metadata(
        metadata={
            "model_name": model_name,
            "lora_rank": lora_rank,
            "wall_clock_seconds": round(time.time() - started, 2),
        }
    )
    return adapter_dir
