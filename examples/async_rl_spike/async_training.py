"""One GRPO optimizer step as a plain function, called by the trainer.

No ZenML step wrapper: `train_step` calls this once per version, reading
its base adapter from one version directory and writing the next version's
adapter to another.
"""

import math
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def _json_safe(value: float) -> "float | str":
    return value if math.isfinite(value) else str(value)


def run_grpo_step(
    episodes: List[Dict[str, Any]],
    base_adapter_dir: Path,
    out_adapter_dir: Path,
    model_name: str,
    group_size: int,
    learning_rate: float,
) -> Dict[str, Any]:
    """Run one GRPO optimizer step and save the next adapter version.

    Episodes must already be deduplicated so each prompt appears exactly
    group_size times (one complete group per task).

    Args:
        episodes: Scored episodes forming complete groups.
        base_adapter_dir: Adapter directory to start training from.
        out_adapter_dir: Directory to save the updated adapter into.
        model_name: HF model ID of the policy base model.
        group_size: GRPO group size.
        learning_rate: Optimizer learning rate.

    Raises:
        ValueError: If episodes do not form complete groups.
        RuntimeError: If training produced non-finite weights.

    Returns:
        Training metrics (JSON-safe).
    """
    import os

    os.environ["TRL_EXPERIMENTAL_SILENCE"] = "1"

    import torch
    from datasets import Dataset
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    by_prompt: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_prompt[episode["prompt_text"]].append(episode)
    for group in by_prompt.values():
        group.sort(key=lambda e: e["rollout_index"])
        if len(group) != group_size:
            raise ValueError(
                f"Task group has {len(group)} episodes, expected {group_size}."
            )
    unique_prompts = list(by_prompt.keys())

    started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    base_model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
    model = PeftModel.from_pretrained(
        base_model, str(base_adapter_dir), is_trainable=True
    )
    model_load_seconds = round(time.time() - started, 2)

    cursor: Dict[str, int] = defaultdict(int)

    def rollout_func(prompts: List[Any], trainer: Any) -> Dict[str, List[Any]]:
        out: Dict[str, List[Any]] = {
            "prompt_ids": [],
            "completion_ids": [],
            "logprobs": [],
            "reward": [],
        }
        for prompt in prompts:
            episode = by_prompt[prompt][cursor[prompt]]
            cursor[prompt] += 1
            out["prompt_ids"].append(episode["prompt_ids"])
            out["completion_ids"].append(episode["completion_ids"])
            out["logprobs"].append(episode["logprobs"])
            out["reward"].append(episode["reward"])
        return out

    def precomputed_reward(
        completions: List[Any],
        reward: Optional[List[float]] = None,
        **kwargs: Any,
    ) -> List[float]:
        assert reward is not None
        return [float(r) for r in reward]

    config = GRPOConfig(
        output_dir=tempfile.mkdtemp(prefix="async-rl-grpo-"),
        per_device_train_batch_size=group_size,
        gradient_accumulation_steps=len(unique_prompts),
        num_generations=group_size,
        max_steps=1,
        learning_rate=learning_rate,
        beta=0.0,
        report_to=[],
        logging_steps=1,
        use_cpu=not (
            torch.cuda.is_available() or torch.backends.mps.is_available()
        ),
        dataloader_pin_memory=False,
    )
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=precomputed_reward,
        args=config,
        train_dataset=Dataset.from_dict({"prompt": unique_prompts}),
        processing_class=tokenizer,
        rollout_func=rollout_func,
    )

    started = time.time()
    train_result = trainer.train()
    train_seconds = round(time.time() - started, 2)

    grad_norm = next(
        (
            entry["grad_norm"]
            for entry in reversed(trainer.state.log_history)
            if "grad_norm" in entry
        ),
        None,
    )

    corrupted = [
        name
        for name, parameter in model.named_parameters()
        if parameter.requires_grad and not torch.isfinite(parameter).all()
    ]
    if corrupted:
        raise RuntimeError(
            f"run_grpo_step produced non-finite weights in {len(corrupted)} "
            f"tensors (grad_norm={grad_norm}); refusing to save the adapter."
        )

    out_adapter_dir.parent.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(out_adapter_dir))

    rewards = [e["reward"] for e in episodes]
    return {
        "num_episodes": len(episodes),
        "num_groups": len(unique_prompts),
        "mean_reward": round(sum(rewards) / len(rewards), 4),
        "train_loss": _json_safe(float(train_result.training_loss)),
        "grad_norm": (
            _json_safe(float(grad_norm)) if grad_norm is not None else -1.0
        ),
        "model_load_seconds": model_load_seconds,
        "train_seconds": train_seconds,
    }
