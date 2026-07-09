"""The update-rule step: gepa.optimize evolves the cheatsheet (Option A).

The whole GEPA inner loop (propose → minibatch-evaluate → accept/reject →
Pareto bookkeeping) runs inside this one step, calling the sandbox directly
rather than through mapped ZenML steps. That choice is itself experiment
evidence for question (a): when the update rule owns its own inner loop,
ZenML's step granularity coarsens from per-episode to per-optimization-run
— the inverse trade of the GRPO pipeline, where every episode was a
visible mapped step. The candidate tree comes back as one artifact
(gepa_result) instead.
"""

from typing import Annotated, Any, Dict, List, Tuple

from zenml import log_metadata, step


@step
def evolve_prompt(
    tasks: List[Dict[str, Any]],
    seed_cheatsheet: str,
    max_metric_calls: int = 60,
    dry_run: bool = True,
) -> Tuple[
    Annotated[str, "evolved_cheatsheet"],
    Annotated[Dict[str, Any], "gepa_result"],
]:
    """Run one GEPA optimization over the cheatsheet.

    Args:
        tasks: Task records; used as both trainset and valset (the spike
            optimizes for capability on THIS task set, not held-out
            generalization — noted in the findings honesty paragraph).
        seed_cheatsheet: Starting candidate (the GRPO baseline's
            CHEATSHEET).
        max_metric_calls: Total episode budget (one metric call = one
            generate + one sandbox score). The spend knob.
        dry_run: Use canned generation/reflection stubs (zero API cost)
            instead of gpt-5-nano / gpt-5.4.

    Returns:
        The best evolved cheatsheet, and the full GEPAResult dict —
        candidates, parents (the lineage tree), per-task val_subscores,
        Pareto frontier membership, plus API usage/cost counters.
    """
    import gepa
    from adapter import CheatsheetAdapter
    from generation import (
        REFLECTION_USAGE,
        TASK_USAGE,
        dry_run_generate,
        dry_run_reflection_lm,
        generate_program,
        reflection_lm,
    )

    adapter = CheatsheetAdapter(
        dry_run_generate if dry_run else generate_program
    )
    result = gepa.optimize(
        seed_candidate={"cheatsheet": seed_cheatsheet},
        trainset=tasks,
        valset=tasks,
        adapter=adapter,
        reflection_lm=dry_run_reflection_lm if dry_run else reflection_lm,
        max_metric_calls=max_metric_calls,
        track_best_outputs=True,
        display_progress_bar=False,
        seed=0,
    )

    result_dict = result.to_dict()
    result_dict["best_idx"] = result.best_idx
    result_dict["usage"] = {
        "task_lm": TASK_USAGE.as_dict(),
        "reflection_lm": REFLECTION_USAGE.as_dict(),
    }

    best_score = result.val_aggregate_scores[result.best_idx]
    log_metadata(
        metadata={
            "dry_run": dry_run,
            "num_candidates": len(result.candidates),
            "best_idx": result.best_idx,
            "best_val_score": best_score,
            "seed_val_score": result.val_aggregate_scores[0],
            "total_metric_calls": result.total_metric_calls or 0,
            **{
                f"{role}_{key}": value
                for role, usage in result_dict["usage"].items()
                for key, value in usage.items()
            },
        }
    )
    return result.best_candidate["cheatsheet"], result_dict
