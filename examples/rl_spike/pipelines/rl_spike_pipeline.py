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
from zenml.enums import StepRuntime

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
    if dry_run:
        init_lora_step = init_lora
        generate_step = generate_rollouts
        episode_step = run_episode
        update_step = grpo_update
    else:
        # Remote placement (see k8s_settings.py and GPU_SETUP.md): the
        # model-loading steps run isolated on the GPU node; episodes run
        # isolated on the CPU pool with the zenml-capable sandbox image.
        from k8s_settings import EPISODE_STEP_SETTINGS, GPU_STEP_SETTINGS

        init_lora_step = init_lora.with_options(
            runtime=StepRuntime.ISOLATED, settings=GPU_STEP_SETTINGS
        )
        generate_step = generate_rollouts.with_options(
            runtime=StepRuntime.ISOLATED, settings=GPU_STEP_SETTINGS
        )
        episode_step = run_episode.with_options(
            runtime=StepRuntime.ISOLATED, settings=EPISODE_STEP_SETTINGS
        )
        update_step = grpo_update.with_options(
            runtime=StepRuntime.ISOLATED, settings=GPU_STEP_SETTINGS
        )

    tasks = load_tasks(task_ids=task_ids, num_tasks=num_tasks)
    adapter = init_lora_step(model_name=model_name, lora_rank=lora_rank)

    for iteration in range(iterations):
        iteration_started = time.time()
        seeds = generate_step(
            tasks=tasks,
            adapter=adapter,
            group_size=group_size,
            model_name=model_name,
            dry_run=dry_run,
        )
        episodes = episode_step.map(seeds)
        adapter = update_step(
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
