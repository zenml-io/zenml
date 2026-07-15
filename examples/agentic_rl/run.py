#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Entrypoint of the agentic RL example.

\b
Tiers:
  --smoke   hermetic eval campaign + gate (oracle vs nop, no API keys)
  --eval    eval campaign + gate with a real agent/model
  --train   sandbox preflight -> prime-rl GRPO (one command step) -> rollout ingest
            -> lineage report. Needs a prime-rl checkout and 2 GPUs.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR))

from pipelines.eval_pipeline import agentic_rl_eval  # noqa: E402
from pipelines.train_pipeline import agentic_rl_train  # noqa: E402

# Only tasks with a committed mechanical oracle solution can run
# hermetically (the oracle agent replays solution/solve.sh).
SMOKE_TASK_IDS = [
    "const_seven",
    "const_greeting",
    "two_step_double",
]


def _task_paths(task_ids: Optional[List[str]] = None) -> List[str]:
    """Resolve generated task directories.

    Args:
        task_ids: Specific task ids, or None for the full taskset.

    Returns:
        Absolute task directory paths.

    Raises:
        click.UsageError: If the taskset has not been generated yet.
    """
    tasks_dir = EXAMPLE_DIR / "tasks"
    if not tasks_dir.is_dir():
        raise click.UsageError(
            "No taskset found. Generate it once first: "
            "python scripts/gen_taskset.py (it is stable across runs; "
            "regenerating changes trial identities and invalidates "
            "shard caching)."
        )
    if task_ids is None:
        return sorted(
            str(path) for path in tasks_dir.iterdir() if path.is_dir()
        )
    return [str(tasks_dir / task_id) for task_id in task_ids]


@click.command(
    help="""Run the agentic RL example.

\b
Examples:
  # Hermetic smoke: oracle vs nop on 3 easy tasks, no API keys needed
  python run.py --smoke

\b
  # Eval campaign with a real agent (needs the relevant API key)
  python run.py --eval --agent terminus-2 --model gpt-5-nano

\b
  # Full tier 1: preflight -> prime-rl -> ingest -> report (2 GPUs)
  python run.py --train --prime-rl-dir ~/prime-rl
"""
)
@click.option("--smoke", is_flag=True, help="Hermetic oracle-vs-nop tier.")
@click.option("--eval", "eval_", is_flag=True, help="Eval campaign tier.")
@click.option("--train", is_flag=True, help="Training tier (2 GPUs).")
@click.option("--agent", default="oracle", help="Harbor agent name.")
@click.option("--model", default=None, help="Model name for the agent.")
@click.option(
    "--trials", default=1, type=int, help="Trials per (task x agent) cell."
)
@click.option(
    "--prime-rl-dir",
    default=os.environ.get("PRIME_RL_DIR", ""),
    help="Path to a prime-rl checkout (or set PRIME_RL_DIR).",
)
@click.option(
    "--output-dir",
    default=str(EXAMPLE_DIR / "prime-rl-output"),
    help="prime-rl --output-dir; later steps read traces/weights here.",
)
@click.option("--no-cache", is_flag=True, help="Disable caching.")
@click.option(
    "--after-eval",
    is_flag=True,
    help="After training, serve the checkpoint, probe it, and stop it "
    "(--train only; provisions a GPU serving pod).",
)
def main(
    smoke: bool,
    eval_: bool,
    train: bool,
    agent: str,
    model: Optional[str],
    trials: int,
    prime_rl_dir: str,
    output_dir: str,
    no_cache: bool,
    after_eval: bool,
) -> None:
    """Run the selected tier.

    Args:
        smoke: Run the hermetic smoke tier.
        eval_: Run the eval tier.
        train: Run the training tier.
        agent: Harbor agent name for eval/gate campaigns.
        model: Model name for the agent, if it needs one.
        trials: Trials per campaign cell.
        prime_rl_dir: prime-rl checkout path for the trainer.
        output_dir: prime-rl output directory.
        no_cache: Disable caching for this run.
        after_eval: Serve/probe/stop the checkpoint after training.
    """
    if sum([smoke, eval_, train]) != 1:
        raise click.UsageError("Pick exactly one of --smoke/--eval/--train.")
    if after_eval and not train:
        raise click.UsageError("--after-eval only applies to --train.")

    pipeline_args: Dict[str, Any] = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    if smoke:
        # Oracle replays each task's committed solution (reward 1.0);
        # nop attempts nothing (reward 0.0). The mean lands mid-window,
        # so the same run also exercises the gate's happy path.
        agentic_rl_eval.with_options(**pipeline_args)(
            tasks=_task_paths(SMOKE_TASK_IDS),
            agents=[{"name": "oracle"}, {"name": "nop"}],
            trials_per_cell=trials,
            min_mean_reward=0.05,
            max_mean_reward=0.98,
        )
        return

    agent_config: Dict[str, Any] = {"name": agent}
    if model:
        agent_config["model_name"] = model

    if eval_:
        agentic_rl_eval.with_options(**pipeline_args)(
            tasks=_task_paths(),
            agents=[agent_config],
            trials_per_cell=trials,
        )
        return

    if not prime_rl_dir:
        raise click.UsageError(
            "--train needs --prime-rl-dir (or PRIME_RL_DIR): a prime-rl "
            "checkout with its uv environment synced. See the README's "
            "Env C section."
        )
    agentic_rl_train.with_options(**pipeline_args)(
        prime_rl_dir=str(Path(prime_rl_dir).expanduser()),
        rl_config=str(EXAMPLE_DIR / "configs" / "rl.toml"),
        output_dir=output_dir,
        after_eval=after_eval,
    )


if __name__ == "__main__":
    main()
