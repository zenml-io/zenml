"""Per-iteration batch generation step."""

import time
from pathlib import Path
from typing import Any, Dict, List

from generation import get_generator

from zenml import log_metadata, step


@step
def generate_rollouts(
    tasks: List[Dict[str, Any]],
    adapter: Path,
    group_size: int,
    model_name: str,
    dry_run: bool,
) -> List[Dict[str, Any]]:
    """Generate group_size completions per task in one batch.

    This is the step that would be a long-lived vLLM server in a mature
    RL system. Here the engine (or the dry-run stub model) is loaded
    fresh every iteration and released when the step exits — the load
    time is recorded in metadata precisely because that repeated cost is
    one of the spike's findings (BREAKAGE_LOG.md entry 2).

    Args:
        tasks: Task records.
        adapter: Current LoRA adapter directory (from init_lora or the
            previous grpo_update).
        group_size: GRPO group size (completions per task).
        model_name: HF model ID of the policy base model.
        dry_run: True = canned completions via StubGenerator (CPU),
            False = vLLM offline batch inference (GPU).

    Returns:
        One episode dict per (task, rollout_index) — see
        generation.EPISODE_KEYS.
    """
    started = time.time()
    generator = get_generator(
        dry_run=dry_run, model_name=model_name, adapter_path=str(adapter)
    )
    engine_load_seconds = round(time.time() - started, 2)

    started = time.time()
    episodes = generator.generate(tasks, group_size)
    generation_seconds = round(time.time() - started, 2)

    completion_tokens = sum(len(e["completion_ids"]) for e in episodes)
    log_metadata(
        metadata={
            "engine_load_seconds": engine_load_seconds,
            "generation_seconds": generation_seconds,
            "num_episodes": len(episodes),
            "completion_tokens": completion_tokens,
            "dry_run": dry_run,
        }
    )
    return episodes
