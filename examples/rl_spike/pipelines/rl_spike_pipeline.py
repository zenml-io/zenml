"""The RL loop as one synchronous dynamic pipeline (v0 of the spike)."""

import time
from typing import List, Optional

from steps import (
    generate_rollouts,
    grpo_update,
    init_lora,
    load_tasks,
    log_iteration_metrics,
    run_episode,
)

from zenml import pipeline

# Caching must stay off: the group_size rollouts of one task have identical
# step inputs, so with caching on, ZenML would serve one sampled completion
# for the whole group -> zero within-group variance -> GRPO advantages all
# zero -> silent learning stop. See BREAKAGE_LOG.md entry 3.


@pipeline(dynamic=True, enable_cache=False)
def rl_spike(
    model_name: str = "Qwen/Qwen3-0.6B",
    iterations: int = 2,
    group_size: int = 4,
    task_ids: Optional[List[str]] = None,
    num_tasks: Optional[int] = None,
    dry_run: bool = True,
    learning_rate: float = 5e-6,
    lora_rank: int = 16,
) -> None:
    """GRPO post-training loop for writing ZenML dynamic pipelines.

    Per iteration: one batched generation step (GPU, or the dry-run
    stub), a sandbox fan-out that runs and scores every completion, and
    one TRL GRPO optimizer step producing the next adapter version. The
    adapter artifact is the thread through the loop — dashboard lineage
    shows adapter vN feeding generation N+1.

    Args:
        model_name: HF model ID of the policy base model.
        iterations: RL iterations (generation -> score -> update).
        group_size: Completions per task (GRPO group size).
        task_ids: Explicit task selection (dry run uses the tasks that
            have canned perfect completions).
        num_tasks: Alternative to task_ids: first N tasks.
        dry_run: True = stub generator, no GPU anywhere.
        learning_rate: GRPO learning rate.
        lora_rank: Rank of the LoRA adapter.
    """
    tasks = load_tasks(task_ids=task_ids, num_tasks=num_tasks)
    adapter = init_lora(model_name=model_name, lora_rank=lora_rank)

    for iteration in range(iterations):
        iteration_started = time.time()
        seeds = generate_rollouts(
            tasks=tasks,
            adapter=adapter,
            group_size=group_size,
            model_name=model_name,
            dry_run=dry_run,
        )
        episodes = run_episode.map(seeds)
        adapter = grpo_update(
            episodes=episodes,
            adapter=adapter,
            model_name=model_name,
            group_size=group_size,
            learning_rate=learning_rate,
        )
        # grpo_update is a synchronous call, so by this line the whole
        # iteration (including all mapped episodes) has finished — the
        # elapsed time is the true iteration wall clock, measured by hand
        # because ZenML has no per-phase cost/timing rollup (finding).
        log_iteration_metrics(
            iteration=iteration,
            episodes=episodes,
            iteration_wall_clock_seconds=time.time() - iteration_started,
        )
