"""C1: a verifiers environment eval as a mapped ZenML campaign.

The question (framework_breakout.md Track C, C1): verifiers already owns
rollout, parsing, and rubric scoring — C2 proved its rubric can open a
ZenML Sandbox per completion. So what does wrapping `env.evaluate(...)`
in a ZenML pipeline add over the bare `vf-eval` CLI? The pipeline here
exists to answer that, not to be infrastructure: one step shards the
task set, mapped steps each run `env.evaluate(...)` for their shard
against a hosted OpenAI-compatible model, one step aggregates into a
dashboard-rendered markdown report.

Sub-questions this file makes observable (verdict in C1_EVAL.md):
(a) `env.evaluate` is async by design, so every mapped step calls
    `asyncio.run` inside the step body — does that behave?
(b) each shard step returns verifiers' results as an HF
    `datasets.Dataset` — what does ZenML's materializer story do
    with it?
(c) the wrapping's alleged value — versioned per-shard artifacts,
    retries on mapped shards, a dashboard report — is any of it real?

Unlike compare_rewards.py this deliberately targets the shared staging
server (project rl-spike, stack rl-spike-local): versioned artifacts on
a real server are the thing being evaluated. The sandbox flavor is
local, so generated pipelines still execute on this machine against
throwaway sqlite stores. Keep the fan-out modest (BREAKAGE_LOG 12/15).

Run from this directory:

    .venv/bin/python c1_eval_pipeline.py --num-tasks 10 --num-shards 2

Requires OPENAI_API_KEY (default model gpt-5-mini).
"""

import argparse
import asyncio
import contextlib
import json
import os
import signal
import statistics
import sys
import threading
from pathlib import Path
from typing import Annotated, Any, Iterator
from unittest import mock

# The local sandbox flavor execs bare `python`; the venv's bin dir must
# lead PATH so that resolves to an interpreter with zenml installed.
os.environ.setdefault("ZENML_ANALYTICS_OPT_IN", "false")
os.environ.setdefault("AUTO_OPEN_DASHBOARD", "false")
os.environ.setdefault("ZENML_ENABLE_RICH_TRACEBACK", "false")
os.environ["PATH"] = f"{Path(sys.executable).parent}:{os.environ['PATH']}"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datasets import Dataset  # noqa: E402
from zenml_pipeline_env import load_environment, load_tasks  # noqa: E402

from zenml import log_metadata, pipeline, step  # noqa: E402
from zenml.types import MarkdownString  # noqa: E402

DEFAULT_MODEL = "gpt-5-mini"


@contextlib.contextmanager
def tolerate_non_main_thread() -> Iterator[None]:
    """Allow verifiers Environment construction off the main thread.

    verifiers 0.1.14 installs SIGINT/SIGTERM teardown handlers in
    Environment.__post_init__ (envs/environment.py), and Python only
    permits signal.signal from the main thread — but ZenML's local
    dynamic runner executes mapped steps in worker threads, so
    load_environment() crashes with "signal only works in main thread".
    Dropping the handlers here is safe: inside a step the rubric's
    sandbox sessions are context-managed and ZenML owns the process
    lifecycle, so verifiers' signal-time teardown has nothing to do.

    Yields:
        None; signal.signal is a no-op inside the block when the
        caller is not on the main thread.
    """
    if threading.current_thread() is threading.main_thread():
        yield
        return
    with mock.patch.object(signal, "signal"):
        yield


def _rollout_row(output: dict, shard_index: int) -> dict[str, Any]:
    """Flatten one verifiers RolloutOutput into an Arrow-safe row.

    Args:
        output: One entry of GenerateOutputs["outputs"].
        shard_index: Which shard produced the rollout.

    Returns:
        Scalar columns (task id, reward, error flags) plus JSON-string
        columns for everything nested.
    """
    from verifiers.utils.save_utils import make_serializable

    def dump(value: Any) -> str:
        return json.dumps(value, default=make_serializable)

    info = output.get("info") or {}
    scorer_result = output.get("scorer_result") or {}
    return {
        "task_id": info.get("task_id", "?"),
        "shard": shard_index,
        "example_id": output.get("example_id"),
        "reward": float(output["reward"]),
        "is_completed": bool(output.get("is_completed")),
        "infra_error": output.get("infra_error"),
        "scorer_error": scorer_result.get("error"),
        "prompt_json": dump(output.get("prompt")),
        "completion_json": dump(output.get("completion")),
        "scorer_result_json": dump(scorer_result),
        "metrics_json": dump(output.get("metrics")),
    }


@step
def make_shards(
    num_tasks: int, num_shards: int, task_ids: list[str] | None = None
) -> list[dict]:
    """Split the selected task ids into round-robin shards.

    Args:
        num_tasks: How many tasks (from the top of tasks.jsonl) to eval
            when task_ids is not given.
        num_shards: How many mapped eval steps to fan out over.
        task_ids: Explicit task selection (overrides num_tasks).

    Returns:
        One dict per shard: {"shard_index": i, "task_ids": [...]}.
    """
    if task_ids is None:
        task_ids = [task["id"] for task in load_tasks()[:num_tasks]]
    return [
        {
            "shard_index": index,
            "task_ids": task_ids[index::num_shards],
        }
        for index in range(num_shards)
        if task_ids[index::num_shards]
    ]


@step(enable_cache=False)
def eval_shard(
    shard: dict,
    model: str,
    rollouts_per_example: int,
) -> Annotated[Dataset, "shard_rollouts"]:
    """Run env.evaluate over one shard against the hosted model.

    Sampling is nondeterministic, so caching stays off (the same
    BREAKAGE_LOG entry-3 hazard as the RL loop's rollout steps).

    Args:
        shard: Shard dict from make_shards.
        model: Hosted model name (OpenAI-compatible chat completions).
        rollouts_per_example: Completions per task (pass@k signal).

    Returns:
        The shard's rollouts as an HF Dataset — deliberately, to answer
        sub-question (b): one row per rollout with prompt, completion,
        reward, and the rubric's infra_error/scorer_result state.
    """
    from verifiers.types import ClientConfig

    with tolerate_non_main_thread():
        env = load_environment(task_ids=shard["task_ids"])
    # ClientConfig defaults point at Prime Intellect's inference cloud
    # (api_key_var=PRIME_API_KEY, api.pinference.ai) — override both.
    client_config = ClientConfig(
        api_key_var="OPENAI_API_KEY",
        api_base_url="https://api.openai.com/v1",
    )
    results = asyncio.run(
        env.evaluate(
            client=client_config,
            model=model,
            rollouts_per_example=rollouts_per_example,
            # In-flight LLM calls; sandbox pressure is separately capped
            # at 4 by the rubric's semaphore (C2_MAX_SANDBOXES).
            max_concurrent=8,
            state_columns=["infra_error", "scorer_result"],
        )
    )
    outputs = results["outputs"]
    metadata = results["metadata"]
    usage = metadata.get("usage") or {}
    log_metadata(
        metadata={
            "shard_index": shard["shard_index"],
            "task_ids": shard["task_ids"],
            "model": model,
            "avg_reward": metadata["avg_reward"],
            "avg_error": metadata["avg_error"],
            "eval_wall_clock_s": round(metadata["time"], 1),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
        }
    )
    # Not env.make_dataset(results): that crashes on its own evaluate
    # outputs (prompt still holds Message model objects Arrow can't
    # type), and heterogeneous nested fields break Arrow's one-schema
    # rule anyway. Scalars stay native columns; anything nested rides
    # as a JSON string.
    return Dataset.from_list(
        [_rollout_row(output, shard["shard_index"]) for output in outputs]
    )


@step
def aggregate_report(
    shard_datasets: list[Dataset], model: str
) -> Annotated[MarkdownString, "eval_report"]:
    """Merge shard rollouts into one campaign report.

    Args:
        shard_datasets: The mapped eval_shard outputs.
        model: The evaluated model name, echoed into the report.

    Returns:
        A markdown report (rendered by the dashboard) with per-task
        rewards and campaign aggregates.
    """
    rows: list[dict[str, Any]] = [
        dict(row) for dataset in shard_datasets for row in dataset
    ]
    rows.sort(key=lambda r: (r["shard"], r["task_id"]))

    rewards = [row["reward"] for row in rows]
    infra_errors = sum(1 for row in rows if row["infra_error"])
    log_metadata(
        metadata={
            "model": model,
            "num_rollouts": len(rows),
            "mean_reward": round(statistics.fmean(rewards), 4),
            "infra_errors": infra_errors,
        }
    )

    lines = [
        f"# C1 verifiers eval campaign — `{model}`",
        "",
        f"{len(rows)} rollouts, mean reward "
        f"**{statistics.fmean(rewards):.4f}**, "
        f"{infra_errors} infra errors.",
        "",
        "| task | shard | reward | infra error | scorer error |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['task_id']} | {row['shard']} | {row['reward']:.2f} "
            f"| {row['infra_error'] or ''} | {row['scorer_error'] or ''} |"
        )
    return MarkdownString("\n".join(lines))


@pipeline(dynamic=True, enable_cache=False)
def c1_verifiers_eval(
    model: str = DEFAULT_MODEL,
    num_tasks: int = 10,
    num_shards: int = 2,
    rollouts_per_example: int = 1,
    task_ids: list[str] | None = None,
) -> None:
    """Sharded verifiers eval campaign: shard -> map evaluate -> report.

    Args:
        model: Hosted model to evaluate.
        num_tasks: Tasks from the top of tasks.jsonl.
        num_shards: Mapped fan-out width (keep modest; each shard also
            opens up to 4 concurrent sandbox sessions for scoring).
        rollouts_per_example: Completions per task.
        task_ids: Explicit task selection (overrides num_tasks).
    """
    shards = make_shards(
        num_tasks=num_tasks, num_shards=num_shards, task_ids=task_ids
    )
    shard_datasets = eval_shard.map(
        shards, model=model, rollouts_per_example=rollouts_per_example
    )
    aggregate_report(shard_datasets=shard_datasets, model=model)


def main() -> None:
    """Parse CLI args and launch the campaign."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--num-tasks", type=int, default=10)
    parser.add_argument("--num-shards", type=int, default=2)
    parser.add_argument("--rollouts-per-example", type=int, default=1)
    parser.add_argument(
        "--task-ids", nargs="*", default=None, help="Explicit task ids"
    )
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set")

    c1_verifiers_eval(
        model=args.model,
        num_tasks=args.num_tasks,
        num_shards=args.num_shards,
        rollouts_per_example=args.rollouts_per_example,
        task_ids=args.task_ids,
    )


if __name__ == "__main__":
    main()
