"""Entrypoint for the trainer pipeline.

Run this in one terminal and run_rollouts.py in another, both with the same
--run-name (they resolve it to the same sub-directory of the active stack's
artifact store):

    python run_trainer.py --run-name async_rl_run --max-train-steps 5
"""

import argparse
import time

from async_shared import resolve_run_root
from pipelines.trainer_pipeline import trainer_pipeline

DEFAULT_RUN_NAME = "async_rl_run"
DEFAULT_MODEL = "Qwen/Qwen3-0.6B"


def main() -> None:
    """Parse args and launch the trainer pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--groups-per-step", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--max-train-steps", type=int, default=5)
    parser.add_argument("--max-versions", type=int, default=3)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--idle-timeout", type=float, default=120.0)
    parser.add_argument("--gc-grace", type=float, default=30.0)
    args = parser.parse_args()

    run_dir = resolve_run_root(args.run_name)
    print(
        f"trainer: run_dir={run_dir} model={args.model} "
        f"max_train_steps={args.max_train_steps} "
        f"max_versions={args.max_versions}"
    )
    started = time.time()
    trainer_pipeline(
        run_dir=run_dir,
        model_name=args.model,
        group_size=args.group_size,
        groups_per_step=args.groups_per_step,
        learning_rate=args.learning_rate,
        lora_rank=args.lora_rank,
        max_train_steps=args.max_train_steps,
        max_versions=args.max_versions,
        poll_interval_seconds=args.poll_interval,
        idle_timeout_seconds=args.idle_timeout,
        gc_grace_seconds=args.gc_grace,
    )
    print(f"trainer done in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
