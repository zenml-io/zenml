"""Run the G1 GEPA cheatsheet-evolution pipeline.

Dry run (no API keys, canned generation, local sandbox):

    .venv/bin/python run.py --dry-run

Real run (needs OPENAI_API_KEY; gpt-5-nano task LM, gpt-5.4 reflection LM):

    .venv/bin/python run.py --max-metric-calls 150
"""

import argparse
import os
import sys
from pathlib import Path


def _ensure_venv_on_path() -> None:
    """Put this venv's bin dir first on PATH.

    The local sandbox flavor executes `python` via a bare subprocess that
    resolves from PATH — without this, every episode fails with "import
    failed" (no zenml in the resolved interpreter), which is
    indistinguishable from a bad completion in the reward JSON.
    """
    venv_bin = str(Path(sys.executable).parent)
    if venv_bin not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] = venv_bin + os.pathsep + os.environ["PATH"]


def main() -> None:
    """Parse args and run the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--num-tasks", type=int, default=12)
    parser.add_argument(
        "--seed",
        choices=["full", "minimal"],
        default="full",
        help="Seed cheatsheet. 'full' = the GRPO baseline's CHEATSHEET "
        "(measured 1.0 with gpt-5-nano on the 12-task subset — no "
        "headroom). 'minimal' = a one-liner, so GEPA must rediscover the "
        "post-cutoff API from sandbox feedback alone.",
    )
    parser.add_argument(
        "--max-metric-calls",
        type=int,
        default=60,
        help="Episode budget: one call = one generate + one sandbox score.",
    )
    args = parser.parse_args()

    _ensure_venv_on_path()
    os.environ.setdefault("ZENML_ANALYTICS_OPT_IN", "false")
    os.environ.setdefault("AUTO_OPEN_DASHBOARD", "false")

    if not args.dry_run and not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is required for a real run (--dry-run?).")

    from reuse import load_rl_spike_module

    if args.seed == "full":
        seed_cheatsheet = load_rl_spike_module("prompts.py").CHEATSHEET
    else:
        seed_cheatsheet = (
            "You write ZenML dynamic pipelines in Python. The zenml "
            "package provides @step and @pipeline decorators.\n"
        )

    from pipelines import gepa_pipeline

    gepa_pipeline(
        seed_cheatsheet=seed_cheatsheet,
        num_tasks=args.num_tasks,
        max_metric_calls=args.max_metric_calls,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
