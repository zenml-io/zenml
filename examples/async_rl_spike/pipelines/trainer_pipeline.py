"""The trainer pipeline: one continuous learner that owns the versions."""

from async_shared import signal_stop, stop_requested
from steps.disaggregated import publish_initial_version, train_step
from steps.init_lora import init_lora

from zenml import pipeline


@pipeline(dynamic=True, enable_cache=False)
def trainer_pipeline(
    run_dir: str,
    model_name: str = "Qwen/Qwen3-0.6B",
    group_size: int = 4,
    groups_per_step: int = 4,
    learning_rate: float = 5e-6,
    lora_rank: int = 16,
    max_train_steps: int = 5,
    max_versions: int = 3,
    poll_interval_seconds: float = 5.0,
    idle_timeout_seconds: float = 120.0,
    gc_grace_seconds: float = 30.0,
) -> None:
    """Bootstrap version 0, then run one train step per iteration.

    Owns the whole version lifecycle: each train step pulls the freshest
    in-window rollouts, runs one GRPO step, publishes a new adapter
    version, and retires versions past the staleness window. Point it and
    the rollout pipeline at the same run_dir.

    Args:
        run_dir: The shared run directory (weights and queue live here).
        model_name: HF model ID of the policy base model.
        group_size: GRPO group size.
        groups_per_step: Target task-groups per train step.
        learning_rate: Optimizer learning rate.
        lora_rank: Rank of the initial LoRA adapter.
        max_train_steps: Number of train steps (versions) to produce.
        max_versions: Staleness window and live-version cap.
        poll_interval_seconds: Sleep between queue polls while waiting.
        idle_timeout_seconds: Give up waiting for rollouts after this long.
        gc_grace_seconds: Grace before deleting a retired adapter.
    """
    adapter = init_lora(model_name=model_name, lora_rank=lora_rank)
    publish_initial_version(run_dir=run_dir, adapter=adapter)

    for _ in range(max_train_steps):
        if stop_requested(run_dir):
            break
        train_step(
            run_dir=run_dir,
            model_name=model_name,
            group_size=group_size,
            groups_per_step=groups_per_step,
            learning_rate=learning_rate,
            max_versions=max_versions,
            poll_interval_seconds=poll_interval_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            gc_grace_seconds=gc_grace_seconds,
        )

    signal_stop(run_dir)
