"""The G1 pipeline: tasks → evolve cheatsheet → report.

Compare with the GRPO pipeline's iteration loop: there the pipeline body
drove N iterations of generate/score/update as separate steps, because the
artifact (LoRA adapter) had to thread between them. Here GEPA drives its
own iterations inside evolve_prompt, so the pipeline is a straight line
and the loop is invisible to the DAG — Option A's trade, recorded in the
findings.
"""

from typing import Any, Dict

from steps import build_report, evolve_prompt, load_gepa_tasks

from zenml import pipeline


@pipeline(enable_cache=False)
def gepa_pipeline(
    seed_cheatsheet: str,
    num_tasks: int = 12,
    max_metric_calls: int = 60,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Evolve the cheatsheet with GEPA and report the candidate tree.

    Caching is off: evolve_prompt calls external LMs and live sandboxes,
    and a cache-hit "optimization" would silently reuse stale candidates
    (same lesson as the GRPO pipeline's scoring steps).

    Args:
        seed_cheatsheet: Starting cheatsheet text.
        num_tasks: Task-subset size.
        max_metric_calls: Episode budget for the optimizer.
        dry_run: Zero-cost stub generation/reflection.

    Returns:
        The gepa_result artifact (candidate tree + scores + usage).
    """
    tasks = load_gepa_tasks(num_tasks=num_tasks)
    evolved_cheatsheet, gepa_result = evolve_prompt(
        tasks=tasks,
        seed_cheatsheet=seed_cheatsheet,
        max_metric_calls=max_metric_calls,
        dry_run=dry_run,
    )
    build_report(gepa_result=gepa_result, tasks=tasks)
    return gepa_result
