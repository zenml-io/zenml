"""The rollout pipeline: continuously spin up parallel episode generators."""

import time
from typing import Any, Dict, List, Optional

from async_shared import get_current, stop_requested
from steps.disaggregated import generate_and_enqueue

from zenml import pipeline


@pipeline(dynamic=True, enable_cache=False)
def rollout_pipeline(
    run_dir: str,
    tasks: List[Dict[str, Any]],
    model_name: str = "Qwen/Qwen3-0.6B",
    group_size: int = 4,
    num_parallel: int = 4,
    dry_run: bool = True,
    temperature: float = 0.9,
    max_tokens: int = 1024,
    first_version_timeout_seconds: float = 300.0,
    max_waves: Optional[int] = None,
) -> None:
    """Generate rollout groups against the current version until stop.

    Waits for the trainer to publish version 0, then repeatedly submits
    num_parallel generator steps per wave. Each generator reads the
    current version itself and enqueues one complete group. Exits when the
    trainer signals stop or max_waves is reached.

    Args:
        run_dir: The shared run directory (weights and queue live here).
        tasks: Task records to cycle through.
        model_name: HF model ID of the policy base model.
        group_size: Completions per task (GRPO group size).
        num_parallel: Generator steps submitted per wave.
        dry_run: True selects the stub generator (CPU).
        temperature: Sampling temperature (vLLM path).
        max_tokens: Generation cap per completion (vLLM path).
        first_version_timeout_seconds: Max wait for the trainer's v0.
        max_waves: Optional cap on waves (None runs until stop).

    Raises:
        RuntimeError: If the trainer publishes no version in time.
    """
    waited = 0.0
    while get_current(run_dir) is None:
        if waited > first_version_timeout_seconds:
            raise RuntimeError(
                "The trainer published no version within "
                f"{first_version_timeout_seconds:.0f}s."
            )
        time.sleep(2.0)
        waited += 2.0

    wave = 0
    index = 0
    while not stop_requested(run_dir):
        if max_waves is not None and wave >= max_waves:
            break
        futures = []
        for _ in range(num_parallel):
            task = tasks[index % len(tasks)]
            index += 1
            futures.append(
                generate_and_enqueue.submit(
                    run_dir=run_dir,
                    task=task,
                    model_name=model_name,
                    group_size=group_size,
                    dry_run=dry_run,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        for future in futures:
            future.result()
        wave += 1
