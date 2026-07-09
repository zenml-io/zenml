"""C2 reward-equivalence experiment: verifiers rubric vs. the spike scorer.

Pushes identical canned completions (stub_completions tiers) through
both reward paths and compares the 0-1 rewards:

- baseline: sandbox_scripts/score_pipeline.py invoked directly as a
  subprocess, exactly as tests/test_reward.py does — the established
  ground truth for the spike's reward.
- rubric: the same completions scored through verifiers' real scoring
  machinery (Rubric.score_group, concurrent on one event loop), where
  each score opens a ZenML Sandbox session and runs the same scorer
  inside it.

No model endpoint is involved on purpose: a live model produces
different completions per call, which can't answer "do the two reward
paths agree on identical inputs?".

Run from this directory:  .venv/bin/python compare_rewards.py

The script is self-bootstrapping: it points ZENML_CONFIG_PATH at a
local throwaway store (./.zenml_config) so nothing touches the shared
staging server, and registers a local-flavor sandbox stack on first
run.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE_DIR = HERE.parent

# Isolation must happen before any zenml import (zenml reads
# ZENML_CONFIG_PATH at import/client-init time), and the venv's bin dir
# must lead PATH so the local sandbox flavor's bare `python` exec
# resolves to an interpreter that has zenml installed.
os.environ["ZENML_CONFIG_PATH"] = str(HERE / ".zenml_config")
os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
os.environ["AUTO_OPEN_DASHBOARD"] = "false"
os.environ["ZENML_ENABLE_RICH_TRACEBACK"] = "false"
os.environ["ZENML_LOGGING_VERBOSITY"] = "WARN"
os.environ["PATH"] = f"{Path(sys.executable).parent}:{os.environ['PATH']}"

sys.path.insert(0, str(EXAMPLE_DIR))
sys.path.insert(0, str(HERE))

from prompts import strip_markdown_fences  # noqa: E402
from stub_completions import canned_completion  # noqa: E402
from zenml_pipeline_env import (  # noqa: E402
    ZenMLSandboxRubric,
    load_tasks,
)

SCORER = EXAMPLE_DIR / "sandbox_scripts" / "score_pipeline.py"
RESULTS_PATH = HERE / "results" / "comparison.json"

# 5 tasks x the stub tiers available for each. PERFECT completions are
# canned for only three tasks (stub_completions.PERFECT); the other two
# tasks get the three generic tiers.
TASK_TIERS = {
    "const_seven": ["perfect", "runs_wrong", "runtime_fail", "syntax_error"],
    "two_step_double": [
        "perfect",
        "runs_wrong",
        "runtime_fail",
        "syntax_error",
    ],
    "map_double_sum": [
        "perfect",
        "runs_wrong",
        "runtime_fail",
        "syntax_error",
    ],
    "const_greeting": ["runs_wrong", "runtime_fail", "syntax_error"],
    "const_list": ["runs_wrong", "runtime_fail", "syntax_error"],
}
TIER_INDEX = {
    "perfect": 0,
    "runs_wrong": 1,
    "runtime_fail": 2,
    "syntax_error": 3,
}


def ensure_local_sandbox_stack() -> None:
    """Register and activate a stack with a local sandbox, idempotently."""
    from zenml.client import Client
    from zenml.enums import StackComponentType

    client = Client()
    components = {
        component.name
        for component in client.list_stack_components(
            type=StackComponentType.SANDBOX.value
        ).items
    }
    if "c2_local_sandbox" not in components:
        client.create_stack_component(
            name="c2_local_sandbox",
            flavor="local",
            component_type=StackComponentType.SANDBOX,
            configuration={},
        )
    stacks = {stack.name for stack in client.list_stacks().items}
    if "c2_stack" not in stacks:
        client.create_stack(
            name="c2_stack",
            components={
                StackComponentType.ORCHESTRATOR: "default",
                StackComponentType.ARTIFACT_STORE: "default",
                StackComponentType.SANDBOX: "c2_local_sandbox",
            },
        )
    client.activate_stack("c2_stack")


def baseline_score(tmp_dir: Path, completion: str, spec: dict) -> dict:
    """Score via the spike scorer directly, as tests/test_reward.py does.

    Args:
        tmp_dir: Scratch directory for this case's files.
        completion: Raw canned completion (possibly fenced).
        spec: Task spec dict.

    Returns:
        The scorer's reward.json dict.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "pipeline.py").write_text(strip_markdown_fences(completion))
    (tmp_dir / "spec.json").write_text(json.dumps(spec))
    result = subprocess.run(
        [
            sys.executable,
            str(SCORER),
            "pipeline.py",
            "spec.json",
            "reward.json",
        ],
        cwd=tmp_dir,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        raise RuntimeError(f"baseline scorer failed: {result.stderr[-800:]}")
    return json.loads((tmp_dir / "reward.json").read_text())


def build_state(task: dict, completion: str) -> dict:
    """Assemble the minimal rollout state Rubric.score_group consumes.

    Args:
        task: Task dict from tasks.jsonl.
        completion: Raw canned completion, shaped as a chat message the
            way a real rollout would record it.

    Returns:
        A state dict with the keys verifiers' scoring path reads.
    """
    return {
        "prompt": [{"role": "user", "content": task["prompt"]}],
        "completion": [{"role": "assistant", "content": completion}],
        "answer": "",
        "info": {"task_id": task["id"], "spec": task["spec"]},
        "task": "rl-spike-pipeline-writing",
        "trajectory": [],
    }


async def rubric_scores(states: list[dict]) -> None:
    """Score all states concurrently through verifiers' machinery.

    Args:
        states: Rollout states; mutated in place with reward/metrics.
    """
    rubric = ZenMLSandboxRubric()
    await rubric.score_group(states)  # type: ignore[arg-type]


def main() -> int:
    """Run the comparison and report agreement.

    Returns:
        Process exit code: 0 if every case matches, 1 otherwise.
    """
    ensure_local_sandbox_stack()

    tasks = {task["id"]: task for task in load_tasks()}
    cases = [
        (task_id, tier)
        for task_id, tiers in TASK_TIERS.items()
        for tier in tiers
    ]
    print(f"{len(cases)} cases (task x completion tier)")

    started = time.time()
    baselines = {}
    scratch = HERE / ".scratch"
    for task_id, tier in cases:
        completion = canned_completion(task_id, TIER_INDEX[tier])
        baselines[(task_id, tier)] = baseline_score(
            scratch / f"{task_id}-{tier}", completion, tasks[task_id]["spec"]
        )
        print(
            f"  baseline {task_id}/{tier}: "
            f"{baselines[(task_id, tier)]['reward']}"
        )
    baseline_s = round(time.time() - started, 1)
    print(f"baseline pass: {baseline_s}s")

    started = time.time()
    states = [
        build_state(
            tasks[task_id], canned_completion(task_id, TIER_INDEX[tier])
        )
        for task_id, tier in cases
    ]
    asyncio.run(rubric_scores(states))
    rubric_s = round(time.time() - started, 1)
    print(f"rubric pass (concurrent sandboxes): {rubric_s}s")

    rows = []
    mismatches = 0
    for (task_id, tier), state in zip(cases, states):
        base = baselines[(task_id, tier)]["reward"]
        via_rubric = state.get("reward")
        infra = state.get("infra_error")
        match = infra is None and abs(base - via_rubric) < 1e-6
        mismatches += 0 if match else 1
        rows.append(
            {
                "task_id": task_id,
                "tier": tier,
                "baseline_reward": base,
                "rubric_reward": via_rubric,
                "match": match,
                "infra_error": infra,
                "scorer_error": (state.get("scorer_result") or {}).get(
                    "error"
                ),
            }
        )
        flag = "OK " if match else "DIFF"
        print(
            f"{flag} {task_id:>16}/{tier:<13} "
            f"baseline={base:<6} rubric={via_rubric:<6} "
            f"{'infra_error=' + infra if infra else ''}"
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "cases": rows,
                "baseline_wall_s": baseline_s,
                "rubric_wall_s": rubric_s,
                "max_concurrent_sandboxes": os.environ.get(
                    "C2_MAX_SANDBOXES", "4"
                ),
                "mismatches": mismatches,
            },
            indent=2,
        )
    )
    print(
        f"\n{len(cases) - mismatches}/{len(cases)} match; "
        f"results -> {RESULTS_PATH.relative_to(HERE)}"
    )
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
