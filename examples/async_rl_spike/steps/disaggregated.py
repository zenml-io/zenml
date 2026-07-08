"""Steps for the disaggregated RL loop: one trainer, many generators."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from async_scoring import score_group
from async_shared import (
    claim_groups,
    discard_group,
    enqueue_group,
    gc_retired,
    get_current,
    init_run_dir,
    is_live,
    live_versions,
    mark_retired,
    publish_version,
    stage_adapter_in,
    stage_adapter_out,
)
from async_training import run_grpo_step
from generation import get_generator

from zenml import log_metadata, step


@step
def publish_initial_version(run_dir: str, adapter: Path) -> None:
    """Bootstrap the run: stage the init adapter as version 0.

    Args:
        run_dir: The shared run directory.
        adapter: The initial LoRA adapter directory from init_lora.
    """
    init_run_dir(run_dir)
    stage_adapter_in(str(adapter), run_dir, 0)
    publish_version(run_dir, 0)


@step
def train_step(
    run_dir: str,
    model_name: str,
    group_size: int,
    groups_per_step: int,
    learning_rate: float,
    max_versions: int,
    poll_interval_seconds: float,
    idle_timeout_seconds: float,
    gc_grace_seconds: float,
) -> int:
    """Run one GRPO step: claim rollouts, train, publish, retire the oldest.

    Waits for fresh rollouts to appear, trains one version from them,
    publishes it, and retires versions past the staleness window.

    Args:
        run_dir: The shared run directory.
        model_name: HF model ID of the policy base model.
        group_size: GRPO group size.
        groups_per_step: Target number of task-groups for this step.
        learning_rate: Optimizer learning rate.
        max_versions: Staleness window; rollouts older than this are
            dropped and versions this far back are retired.
        poll_interval_seconds: Sleep between queue polls while waiting.
        idle_timeout_seconds: Give up waiting for rollouts after this long.
        gc_grace_seconds: Grace before deleting a retired adapter.

    Raises:
        RuntimeError: If no rollouts arrive within idle_timeout_seconds.

    Returns:
        The version produced by this step.
    """
    waited = 0.0
    while True:
        current = get_current(run_dir)
        min_version = current - max_versions + 1
        result = claim_groups(
            run_dir, max_groups=groups_per_step, min_version=min_version
        )
        if result.groups:
            break
        if waited >= idle_timeout_seconds:
            raise RuntimeError(
                f"No rollouts within {idle_timeout_seconds:.0f}s "
                f"(queue below v{min_version})."
            )
        time.sleep(poll_interval_seconds)
        waited += poll_interval_seconds

    # Keep the freshest group per task; a GRPO batch needs distinct
    # prompts, and duplicate tasks are staler by construction.
    deduped: Dict[str, Any] = {}
    dropped_dup = 0
    consumed = []
    for group in result.groups:
        consumed.append(group.path)
        key = group.episodes[0]["prompt_text"]
        if key in deduped:
            dropped_dup += 1
            continue
        deduped[key] = group
    groups = list(deduped.values())
    episodes = [e for group in groups for e in group.episodes]
    staleness = [current - group.version for group in groups]

    new_version = current + 1
    base_local = stage_adapter_out(run_dir, current)
    out_local = os.path.join(tempfile.mkdtemp(prefix="async-rl-out-"), "adapter")
    try:
        metrics = run_grpo_step(
            episodes=episodes,
            base_adapter_dir=Path(base_local),
            out_adapter_dir=Path(out_local),
            model_name=model_name,
            group_size=group_size,
            learning_rate=learning_rate,
        )
        stage_adapter_in(out_local, run_dir, new_version)
    finally:
        shutil.rmtree(base_local, ignore_errors=True)
        shutil.rmtree(os.path.dirname(out_local), ignore_errors=True)
    publish_version(run_dir, new_version)

    keep_from = new_version - max_versions + 1
    for version in live_versions(run_dir):
        if version < keep_from:
            mark_retired(run_dir, version)
    gc_retired(run_dir, gc_grace_seconds)

    for path in consumed:
        discard_group(path)

    mean_staleness = round(sum(staleness) / len(staleness), 2)
    print(
        f"[trainer] v{new_version} groups={len(groups)} "
        f"stale~{mean_staleness} reward={metrics['mean_reward']}"
    )
    log_metadata(
        metadata={
            "trained_version": new_version,
            "base_version": current,
            "groups_trained": len(groups),
            "dropped_stale": result.dropped_stale,
            "dropped_duplicate": dropped_dup,
            "mean_staleness": mean_staleness,
            "max_staleness": max(staleness),
            **metrics,
        }
    )
    return new_version


@step
def generate_and_enqueue(
    run_dir: str,
    task: Dict[str, Any],
    model_name: str,
    group_size: int,
    dry_run: bool,
    temperature: float,
    max_tokens: int,
) -> None:
    """Generate one group against the current version, score it, enqueue it.

    Never raises. Aborts gracefully if the target version is retired
    before the group is enqueued, so a version shutdown mid-generation
    does not crash the rollout pipeline.

    Args:
        run_dir: The shared run directory.
        task: The task record to generate a group for.
        model_name: HF model ID of the policy base model.
        group_size: Completions per task (GRPO group size).
        dry_run: True selects the stub generator (CPU).
        temperature: Sampling temperature (vLLM path).
        max_tokens: Generation cap per completion (vLLM path).
    """
    info: Dict[str, Any] = {"task_id": task.get("id", "?")}
    local_adapter = None
    try:
        version = get_current(run_dir)
        if version is None:
            info["skipped"] = "no_version"
        elif not is_live(run_dir, version):
            info["skipped"] = "version_not_live"
        else:
            local_adapter = stage_adapter_out(run_dir, version)
            generator = get_generator(
                dry_run=dry_run,
                model_name=model_name,
                adapter_path=local_adapter,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            episodes = score_group(generator.generate([task], group_size))

            if not is_live(run_dir, version):
                info["dropped_stale"] = True
                info["version"] = version
            else:
                enqueue_group(run_dir, version, episodes)
                info["version"] = version
                info["enqueued"] = True
                info["mean_reward"] = round(
                    sum(e["reward"] for e in episodes) / len(episodes), 4
                )
    except Exception as e:
        info["infra_error"] = f"{type(e).__name__}: {e}"
    finally:
        if local_adapter:
            shutil.rmtree(local_adapter, ignore_errors=True)

    log_metadata(metadata=info)
