"""Load the task set."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from zenml import step


@step
def load_tasks(
    task_file: str = "tasks/tasks.jsonl",
    task_ids: Optional[List[str]] = None,
    num_tasks: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Read task records from the JSONL task set.

    Args:
        task_file: Path to tasks.jsonl, relative to the example directory.
        task_ids: If given, select exactly these tasks (in this order).
        num_tasks: If given (and task_ids is not), take the first N tasks.

    Returns:
        Task records: {id, difficulty, prompt, spec}.

    Raises:
        ValueError: If a requested task id does not exist.
    """
    path = Path(__file__).resolve().parent.parent / task_file
    with open(path) as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    if task_ids is not None:
        by_id = {task["id"]: task for task in tasks}
        missing = [task_id for task_id in task_ids if task_id not in by_id]
        if missing:
            raise ValueError(f"Unknown task ids: {missing}")
        return [by_id[task_id] for task_id in task_ids]
    if num_tasks is not None:
        return tasks[:num_tasks]
    return tasks
