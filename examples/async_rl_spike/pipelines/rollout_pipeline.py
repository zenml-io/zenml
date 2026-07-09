"""The rollout pipeline: continuously spin up parallel episode generators."""

import time
from typing import Any, Dict, List, Optional

from async_shared import get_current, stop_requested
from remote_settings import FULL_DOCKER
from steps.disaggregated import generate_and_enqueue

from zenml import pipeline


@pipeline(dynamic=True, enable_cache=False, settings={"docker": FULL_DOCKER})
def rollout_pipeline(
    run_dir: str,
    tasks: List[Dict[str, Any]],
    model_name: str = "Qwen/Qwen3-0.6B",
    group_size: int = 4,
    num_parallel: int = 4,
    dry_run: bool = True,
    temperature: float = 0.9,
    max_tokens: int = 1024,
    serving_mode: str = "local",
    first_version_timeout_seconds: float = 300.0,
    poll_interval_seconds: float = 2.0,
    max_rollouts: Optional[int] = None,
) -> None:
    """Generate rollout groups against the current version until stop.

    Waits for the trainer to publish version 0, then keeps a rolling pool
    of num_parallel generators in flight: as each finishes it frees a slot
    and a new generator launches immediately, so the slowest generator does
    not stall the others. Each generator reads the current version itself
    and enqueues one complete group. Exits when the trainer signals stop or
    max_rollouts generators have been launched.

    Args:
        run_dir: The shared run directory (weights and queue live here).
        tasks: Task records to cycle through.
        model_name: HF model ID of the policy base model.
        group_size: Completions per task (GRPO group size).
        num_parallel: Generators kept in flight at once.
        dry_run: True selects the stub generator (CPU, local only).
        temperature: Sampling temperature (vLLM path).
        max_tokens: Generation cap per completion (vLLM path).
        serving_mode: "local" loads the adapter from disk and runs vLLM in
            the generator; "remote" calls each version's vLLM endpoint.
        first_version_timeout_seconds: Max wait for the trainer's v0.
        poll_interval_seconds: Sleep between polls of the in-flight pool.
        max_rollouts: Optional cap on total generators launched (None runs
            until stop).

    Raises:
        ValueError: If serving_mode is unknown or remote is misconfigured.
        RuntimeError: If the trainer publishes no version in time.
    """
    if serving_mode not in {"local", "remote"}:
        raise ValueError(
            f"serving_mode must be 'local' or 'remote', got {serving_mode!r}."
        )
    if serving_mode == "remote" and dry_run:
        raise ValueError("serving_mode='remote' does not support dry_run.")

    waited = 0.0
    while get_current(run_dir) is None:
        if waited > first_version_timeout_seconds:
            raise RuntimeError(
                "The trainer published no version within "
                f"{first_version_timeout_seconds:.0f}s."
            )
        time.sleep(2.0)
        waited += 2.0

    def harvest(future: Any) -> None:
        try:
            future.result()
        except Exception as e:
            print(f"[rollout] generator failed, continuing: {e}")

    in_flight = []
    launched = 0
    while not stop_requested(run_dir):
        while len(in_flight) < num_parallel and (
            max_rollouts is None or launched < max_rollouts
        ):
            task = tasks[launched % len(tasks)]
            in_flight.append(
                generate_and_enqueue.submit(
                    run_dir=run_dir,
                    task=task,
                    model_name=model_name,
                    group_size=group_size,
                    dry_run=dry_run,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    serving_mode=serving_mode,
                )
            )
            launched += 1

        for future in [f for f in in_flight if not f.running()]:
            harvest(future)
            in_flight.remove(future)

        if max_rollouts is not None and launched >= max_rollouts:
            if not in_flight:
                break

        time.sleep(poll_interval_seconds)

    for future in in_flight:
        harvest(future)
