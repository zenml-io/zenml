"""Exact reward values for the canned completions (Stage 1 bar).

Each case invokes sandbox_scripts/score_pipeline.py the way run_episode
does — as a subprocess — so the test exercises the real scoring path,
including the throwaway-ZenML-store isolation and the actual execution of
the generated pipeline. Slow (each scorer call initializes a fresh local
sqlite store and runs a real pipeline); that slowness is itself a
measured finding.

Run from the example directory:  pytest tests/test_reward.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXAMPLE_DIR))

from prompts import strip_markdown_fences  # noqa: E402
from stub_completions import (  # noqa: E402
    PERFECT,
    RUNS_WRONG,
    RUNTIME_FAIL,
    SYNTAX_ERROR,
)

SCORER = EXAMPLE_DIR / "sandbox_scripts" / "score_pipeline.py"
TASKS = {
    json.loads(line)["id"]: json.loads(line)
    for line in (EXAMPLE_DIR / "tasks" / "tasks.jsonl")
    .read_text()
    .splitlines()
}


def score(tmp_path: Path, completion: str, spec: dict) -> dict:
    """Run the scorer exactly as run_episode does inside the sandbox.

    Mirrors the generation layer: the scorer receives the
    fence-stripped program, never the raw completion (RUNS_WRONG is
    deliberately fenced to exercise this).
    """
    (tmp_path / "pipeline.py").write_text(strip_markdown_fences(completion))
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    result = subprocess.run(
        [
            sys.executable,
            str(SCORER),
            "pipeline.py",
            "spec.json",
            "reward.json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads((tmp_path / "reward.json").read_text())


# (completion, task_id, exact expected reward)
CASES = [
    # parses + imports + runs green + both clauses (min_steps=1, value=7)
    ("perfect", "const_seven", 1.0),
    # runs green; min_steps=1 satisfied, expected value 999999 != 7
    # -> 0.3 + 0.4 + 0.3 * (1/2) = 0.85
    ("runs_wrong", "const_seven", 0.85),
    # parses + imports, crashes at run time -> 0.3
    ("runtime_fail", "const_seven", 0.3),
    # not Python -> 0.0
    ("syntax_error", "const_seven", 0.0),
    # 3-clause task: min_steps=6, required '.map(', value 20 -> all met
    ("perfect", "map_double_sum", 1.0),
    # runs green but 1 step, no .map, wrong value -> 0.3 + 0.4 + 0 = 0.7
    ("runs_wrong", "map_double_sum", 0.7),
]

COMPLETIONS = {
    "runs_wrong": RUNS_WRONG,
    "runtime_fail": RUNTIME_FAIL,
    "syntax_error": SYNTAX_ERROR,
}


@pytest.mark.parametrize("tier,task_id,expected", CASES)
def test_exact_reward(
    tmp_path: Path, tier: str, task_id: str, expected: float
):
    """Every canned completion earns its exact expected reward."""
    completion = PERFECT[task_id] if tier == "perfect" else COMPLETIONS[tier]
    result = score(tmp_path, completion, TASKS[task_id]["spec"])
    assert result["reward"] == pytest.approx(expected), json.dumps(
        result, indent=2
    )


def test_perfect_two_step(tmp_path: Path):
    """The third canned dry-run task also scores 1.0."""
    result = score(
        tmp_path, PERFECT["two_step_double"], TASKS["two_step_double"]["spec"]
    )
    assert result["reward"] == pytest.approx(1.0), json.dumps(result, indent=2)
