"""Entrypoint for the RL spike.

Dry run (no GPU, stub completions, local stack + local sandbox):

    python run.py --dry-run

Real run (GPU stack with vLLM installed — see GPU_SETUP.md):

    python run.py --model Qwen/Qwen3-4B-Instruct-2507 \\
        --iterations 5 --group-size 8 --num-tasks 50
"""

import argparse
import sys
import time

from pipelines import rl_spike
from stub_completions import PERFECT

from zenml.client import Client

DRY_RUN_MODEL = "Qwen/Qwen3-0.6B"


def main() -> None:
    """Parse CLI args, validate the stack, and launch the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--serving-mode",
        choices=["offline", "warm_vllm"],
        default="offline",
        help=(
            "offline loads vLLM inside each generation step; warm_vllm "
            "uses a long-lived Kubernetes vLLM server and hot-loads "
            "ZenML LoRA adapter artifacts"
        ),
    )
    parser.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--group-size", type=int, default=None)
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument(
        "--task-ids", nargs="*", default=None, help="Explicit task ids"
    )
    parser.add_argument(
        "--task-ids-file",
        default=None,
        help=(
            "File with one task id per line (# comments allowed), e.g. "
            "tasks/training_mix_v1.txt. Mutually exclusive with --task-ids"
        ),
    )
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.9,
        help="Sampling temperature for rollout generation",
    )
    args = parser.parse_args()

    if args.task_ids_file:
        if args.task_ids:
            sys.exit("Use either --task-ids or --task-ids-file, not both")
        with open(args.task_ids_file) as f:
            args.task_ids = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]

    stack = Client().active_stack
    if stack.sandbox is None:
        sys.exit(
            f"Active stack '{stack.name}' has no sandbox component.\n"
            "Register one and add it to a stack, e.g.:\n"
            "  zenml sandbox register local_sandbox --flavor=local\n"
            "  zenml stack register rl-local -o default -a default "
            "-sb local_sandbox --set"
        )

    if args.dry_run:
        if args.serving_mode != "offline":
            sys.exit("--dry-run only supports --serving-mode offline")
        if args.model != parser.get_default("model"):
            print(
                f"note: --model {args.model} is ignored in dry-run mode; "
                f"the dry run always uses {DRY_RUN_MODEL}"
            )
        model = DRY_RUN_MODEL
        iterations = args.iterations or 2
        group_size = args.group_size or 4
        # Dry-run tasks are limited to those with canned perfect
        # completions (the stub raises on anything else, on purpose).
        task_ids = args.task_ids or sorted(PERFECT)
        num_tasks = None
    else:
        model = args.model
        iterations = args.iterations or 5
        group_size = args.group_size or 8
        task_ids = args.task_ids
        num_tasks = args.num_tasks or 50

    print(
        f"rl_spike: model={model} iterations={iterations} "
        f"group_size={group_size} dry_run={args.dry_run} "
        f"serving_mode={args.serving_mode} "
        f"stack={stack.name} sandbox={stack.sandbox.flavor}"
    )
    pipeline = rl_spike
    if not args.dry_run:
        # Docker settings must attach before submission — the image is
        # built client-side, before the pipeline function ever runs.
        from k8s_settings import DOCKER_SETTINGS, ORCHESTRATOR_ON_GPU_NODE

        pipeline = rl_spike.with_options(
            settings={
                "docker": DOCKER_SETTINGS,
                "orchestrator.kubernetes": ORCHESTRATOR_ON_GPU_NODE,
            }
        )
    started = time.time()
    pipeline(
        model_name=model,
        iterations=iterations,
        group_size=group_size,
        task_ids=task_ids,
        num_tasks=num_tasks,
        dry_run=args.dry_run,
        serving_mode=args.serving_mode,
        learning_rate=args.learning_rate,
        temperature=args.temperature,
    )
    print(f"total wall clock: {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
