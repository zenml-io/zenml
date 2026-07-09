"""Entrypoint for the rollout pipeline.

Run this alongside run_trainer.py, both pointed at the same --run-dir:

    python run_rollouts.py --run-dir ./async_rl_run --num-parallel 4

The dry run restricts tasks to those with canned perfect completions (the
stub raises on anything else, on purpose).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from async_shared import resolve_run_root
from pipelines.rollout_pipeline import rollout_pipeline
from stub_completions import PERFECT

from zenml.client import Client

DEFAULT_RUN_NAME = "async_rl_run"
DEFAULT_MODEL = "Qwen/Qwen3-0.6B"
TASKS_FILE = Path(__file__).resolve().parent / "tasks" / "tasks.jsonl"


def load_task_records(
    task_ids: Optional[List[str]], num_tasks: Optional[int]
) -> List[Dict[str, Any]]:
    """Read task records from the JSONL task set.

    Args:
        task_ids: If given, select exactly these tasks.
        num_tasks: If given (and task_ids is not), take the first N tasks.

    Raises:
        ValueError: If a requested task id does not exist.

    Returns:
        Task records.
    """
    with open(TASKS_FILE) as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    if task_ids is not None:
        by_id = {task["id"]: task for task in tasks}
        missing = [tid for tid in task_ids if tid not in by_id]
        if missing:
            raise ValueError(f"Unknown task ids: {missing}")
        return [by_id[tid] for tid in task_ids]
    if num_tasks is not None:
        return tasks[:num_tasks]
    return tasks


def main() -> None:
    """Parse args, validate the stack, and launch the rollout pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--num-parallel", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument(
        "--serving-mode", choices=["local", "remote"], default="local"
    )
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--max-rollouts", type=int, default=None)
    parser.add_argument("--first-version-timeout", type=float, default=300.0)
    args = parser.parse_args()

    if Client().active_stack.sandbox is None:
        sys.exit(
            "The active stack has no sandbox component. Register one, e.g.:\n"
            "  zenml sandbox register local_sandbox --flavor=local\n"
            "  zenml stack register rl-local -o default -a default "
            "-sb local_sandbox --set"
        )

    # Remote serving has no stub path, so it is always a real (non-dry) run.
    dry_run = args.dry_run if args.serving_mode == "local" else False

    if dry_run:
        task_ids = args.task_ids or sorted(PERFECT)
        num_tasks = None
    else:
        task_ids = args.task_ids
        num_tasks = args.num_tasks or 50
    tasks = load_task_records(task_ids, num_tasks)

    run_dir = resolve_run_root(args.run_name)
    print(
        f"rollouts: run_dir={run_dir} model={args.model} "
        f"serving_mode={args.serving_mode} "
        f"num_parallel={args.num_parallel} dry_run={dry_run} "
        f"tasks={len(tasks)}"
    )
    rollout_pipeline(
        run_dir=run_dir,
        tasks=tasks,
        model_name=args.model,
        group_size=args.group_size,
        num_parallel=args.num_parallel,
        dry_run=dry_run,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        serving_mode=args.serving_mode,
        first_version_timeout_seconds=args.first_version_timeout,
        max_rollouts=args.max_rollouts,
    )


if __name__ == "__main__":
    main()
