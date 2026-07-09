"""Render the GEPA candidate tree as a human-readable markdown artifact.

This is the question-(b) probe: GEPAResult is a TREE (parents[i] is the
lineage edge), and per_val_instance_best_candidates makes "best" a
per-task notion, not a global one. ZenML's artifact versioning is linear,
so the tree is carried inside artifacts (the dict + this report) rather
than by the version graph — whether that is good enough is a finding, not
a given.
"""

from typing import Annotated, Any, Dict, List

from zenml import log_metadata, step


@step
def build_report(
    gepa_result: Dict[str, Any], tasks: List[Dict[str, Any]]
) -> Annotated[str, "gepa_report"]:
    """Summarize candidates, lineage, per-task scores, and API usage.

    Args:
        gepa_result: The serialized GEPAResult from evolve_prompt.
        tasks: The task records (for id column headers).

    Returns:
        Markdown report.
    """
    candidates = gepa_result["candidates"]
    parents = gepa_result["parents"]
    aggregate = gepa_result["val_aggregate_scores"]
    subscores = gepa_result["val_subscores"]
    best_idx = gepa_result["best_idx"]
    frontier = gepa_result["per_val_instance_best_candidates"]
    task_ids = [task["id"] for task in tasks]

    lines = [
        "# GEPA cheatsheet evolution report",
        "",
        f"Candidates: {len(candidates)}  |  best: #{best_idx} "
        f"(val {aggregate[best_idx]:.3f}, seed was {aggregate[0]:.3f})  |  "
        f"metric calls: {gepa_result.get('total_metric_calls')}",
        "",
        "## Candidate tree",
        "",
        "| # | parent | val score | on Pareto frontier for |",
        "|---|--------|-----------|------------------------|",
    ]
    for index in range(len(candidates)):
        wins = [
            task_ids[int(val_id)]
            for val_id, front in frontier.items()
            if index in front and int(val_id) < len(task_ids)
        ]
        parent = parents[index]
        parent_label = (
            ", ".join(str(p) for p in parent)
            if isinstance(parent, list)
            else parent
        )
        lines.append(
            f"| {index} | {parent_label} | {aggregate[index]:.3f} | "
            f"{', '.join(wins) if wins else '—'} |"
        )

    lines += ["", "## Per-task scores", ""]
    lines.append("| candidate | " + " | ".join(task_ids) + " |")
    lines.append("|---|" + "---|" * len(task_ids))
    # Each row is a dict keyed by val-instance id as a STRING ("0".."11").
    for index, scores in enumerate(subscores):
        row = " | ".join(
            f"{scores.get(str(position), float('nan')):.2f}"
            for position in range(len(task_ids))
        )
        lines.append(f"| {index} | {row} |")

    usage = gepa_result.get("usage", {})
    lines += ["", "## API usage", ""]
    for role, counters in usage.items():
        lines.append(f"- **{role}**: {counters}")

    lines += ["", "## Best cheatsheet", "", "```", ""]
    lines.append(candidates[best_idx]["cheatsheet"])
    lines += ["```", ""]

    report = "\n".join(lines)
    log_metadata(metadata={"report_chars": len(report), "best_idx": best_idx})
    return report
