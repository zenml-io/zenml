"""The RL loop as one synchronous dynamic pipeline (v0 of the spike)."""

import time
from typing import List, Optional

from steps import (
    delete_vllm_server,
    ensure_vllm_server,
    generate_rollouts,
    generate_rollouts_from_endpoint,
    grpo_update,
    init_lora,
    load_adapter_into_vllm,
    load_tasks,
    log_iteration_metrics,
    run_episode,
)

from zenml import pipeline
from zenml.config.retry_config import StepRetryConfig
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
    serving_mode: str = "offline",
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
        serving_mode: "offline" loads vLLM inside generate_rollouts;
            "warm_vllm" uses a long-lived Kubernetes vLLM service and
            hot-loads each ZenML LoRA adapter artifact into it.
        learning_rate: GRPO learning rate.
        lora_rank: Rank of the LoRA adapter.
    """
    if dry_run and serving_mode != "offline":
        raise ValueError("dry_run only supports serving_mode='offline'.")
    if serving_mode not in {"offline", "warm_vllm"}:
        raise ValueError(
            "serving_mode must be either 'offline' or 'warm_vllm', got "
            f"{serving_mode!r}."
        )

    if dry_run:
        init_lora_step = init_lora
        generate_step = generate_rollouts
        episode_step = run_episode
        update_step = grpo_update
        delete_server_step = delete_vllm_server
        ensure_server_step = ensure_vllm_server
        load_adapter_step = load_adapter_into_vllm
        generate_http_step = generate_rollouts_from_endpoint
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
            runtime=StepRuntime.ISOLATED,
            settings=EPISODE_STEP_SETTINGS,
            # The mapped fan-out has no working concurrency cap (see
            # BREAKAGE_LOG entry 12), so N pods hit the server at once
            # and some die on 429 rate limits before the step body
            # runs. Retries let those pods come back after the burst.
            retry=StepRetryConfig(max_retries=3, delay=30, backoff=2),
        )
        update_step = grpo_update.with_options(
            runtime=StepRuntime.ISOLATED, settings=GPU_STEP_SETTINGS
        )
        delete_server_step = delete_vllm_server
        ensure_server_step = ensure_vllm_server
        load_adapter_step = load_adapter_into_vllm
        generate_http_step = generate_rollouts_from_endpoint

    tasks = load_tasks(task_ids=task_ids, num_tasks=num_tasks)
    adapter = init_lora_step(model_name=model_name, lora_rank=lora_rank)

    if serving_mode == "warm_vllm":
        from k8s_settings import (
            VLLM_DEPLOYMENT_NAME,
            VLLM_NAMESPACE,
            VLLM_SERVER_IMAGE,
            VLLM_SERVICE_ACCOUNT_NAME,
            VLLM_SERVICE_NAME,
        )

        endpoint = ensure_server_step(
            model_name=model_name,
            image=VLLM_SERVER_IMAGE,
            namespace=VLLM_NAMESPACE,
            deployment_name=VLLM_DEPLOYMENT_NAME,
            service_name=VLLM_SERVICE_NAME,
            max_lora_rank=lora_rank,
            service_account_name=VLLM_SERVICE_ACCOUNT_NAME,
        )
        loaded_adapter = load_adapter_step(
            adapter=adapter,
            endpoint=endpoint,
            adapter_name="rl-spike-iter-000",
        )
    else:
        endpoint = None
        loaded_adapter = None

    for iteration in range(iterations):
        iteration_started = time.time()
        if serving_mode == "warm_vllm":
            assert endpoint is not None
            assert loaded_adapter is not None
            seeds = generate_http_step(
                tasks=tasks,
                endpoint=endpoint,
                loaded_adapter=loaded_adapter,
                group_size=group_size,
                model_name=model_name,
            )
        else:
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
        if serving_mode == "warm_vllm" and iteration < iterations - 1:
            assert endpoint is not None
            loaded_adapter = load_adapter_step(
                adapter=adapter,
                endpoint=endpoint,
                adapter_name=f"rl-spike-iter-{iteration + 1:03d}",
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

    if serving_mode == "warm_vllm":
        assert endpoint is not None
        delete_server_step(endpoint=endpoint, final_adapter=adapter)
