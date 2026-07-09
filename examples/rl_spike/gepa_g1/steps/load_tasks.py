"""Load a difficulty-spread subset of the parent example's tasks."""

import json
from pathlib import Path
from typing import Any, Dict, List

from zenml import log_metadata, step

TASKS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "tasks" / "tasks.jsonl"
)


@step
def load_gepa_tasks(num_tasks: int = 12) -> List[Dict[str, Any]]:
    """Select tasks evenly across the difficulty range.

    A stride over the difficulty-sorted list keeps the subset stable run to
    run (deterministic lineage) while covering easy and hard tasks — GEPA's
    Pareto selection is only interesting if candidates can win on some
    tasks and lose on others.

    Args:
        num_tasks: Size of the subset.

    Returns:
        Task records (id, prompt, spec) from tasks.jsonl.
    """
    tasks = [
        json.loads(line)
        for line in TASKS_PATH.read_text().splitlines()
        if line.strip()
    ]
    tasks.sort(key=lambda task: (task.get("difficulty", 0), task["id"]))
    stride = max(len(tasks) // num_tasks, 1)
    subset = tasks[::stride][:num_tasks]
    log_metadata(
        metadata={
            "num_tasks": len(subset),
            "task_ids": [task["id"] for task in subset],
        }
    )
    return subset
