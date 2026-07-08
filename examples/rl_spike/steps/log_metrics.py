"""Per-iteration metrics aggregation."""

from typing import Annotated, Any, Dict, List

from zenml import log_metadata, step
from zenml.types import MarkdownString


@step
def log_iteration_metrics(
    iteration: int,
    episodes: List[Dict[str, Any]],
    iteration_wall_clock_seconds: float,
) -> Annotated[MarkdownString, "iteration_report"]:
    """Aggregate one iteration's episodes into metrics + a report artifact.

    ZenML has no scalar-timeseries concept (no "reward curve over
    iterations" primitive), so metrics land in two places: run metadata
    (machine-readable) and a markdown artifact (human-readable in the
    dashboard). Stitching curves across iterations by hand is one of the
    spike's expected findings.

    Args:
        iteration: Iteration index.
        episodes: Scored episode dicts from run_episode.
        iteration_wall_clock_seconds: Wall clock of the whole iteration,
            measured in the pipeline function (by-hand cost capture).

    Returns:
        Markdown report artifact.
    """
    rewards = [e["reward"] for e in episodes]
    # error = the generated code was bad (expected, healthy signal);
    # infra_error = the episode harness itself broke (must stay at 0).
    scored_failures = [e for e in episodes if e["error"]]
    infra_errors = [e for e in episodes if e.get("infra_error")]
    mean_reward = sum(rewards) / len(rewards) if rewards else 0.0
    completion_tokens = sum(len(e["completion_ids"]) for e in episodes)

    by_task: Dict[str, List[float]] = {}
    for e in episodes:
        by_task.setdefault(e["task_id"], []).append(e["reward"])

    # Within-group variance is GRPO's lifeblood: a group where every
    # rollout scores the same contributes zero gradient.
    flat_groups = sum(1 for group in by_task.values() if len(set(group)) <= 1)

    metrics = {
        f"iteration_{iteration}.mean_reward": round(mean_reward, 4),
        f"iteration_{iteration}.max_reward": max(rewards, default=0.0),
        f"iteration_{iteration}.min_reward": min(rewards, default=0.0),
        f"iteration_{iteration}.num_episodes": len(episodes),
        f"iteration_{iteration}.num_scored_failures": len(scored_failures),
        f"iteration_{iteration}.num_infra_errors": len(infra_errors),
        f"iteration_{iteration}.flat_groups": flat_groups,
        f"iteration_{iteration}.completion_tokens": completion_tokens,
        f"iteration_{iteration}.wall_clock_seconds": round(
            iteration_wall_clock_seconds, 1
        ),
    }
    log_metadata(metadata=metrics)

    lines = [
        f"# Iteration {iteration}",
        "",
        f"- episodes: **{len(episodes)}** "
        f"({len(scored_failures)} scored as failing code, "
        f"{len(infra_errors)} harness/infra errors)",
        f"- reward: mean **{mean_reward:.3f}**, "
        f"min {min(rewards, default=0):.2f}, max {max(rewards, default=0):.2f}",
        f"- flat groups (no variance -> no gradient): {flat_groups}/{len(by_task)}",
        f"- completion tokens: {completion_tokens}",
        f"- iteration wall clock: {iteration_wall_clock_seconds:.0f}s",
        "",
        "| Task | Rewards |",
        "|---|---|",
    ]
    for task_id, group in sorted(by_task.items()):
        lines.append(f"| {task_id} | {', '.join(f'{r:.2f}' for r in group)} |")
    return MarkdownString("\n".join(lines))
