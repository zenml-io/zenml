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


# (completion, task_id, exact expected reward) — weights 0.2/0.3/0.5
CASES = [
    # parses + imports + runs green + both clauses (min_steps=1, value=7)
    ("perfect", "const_seven", 1.0),
    # runs green; min_steps=1 satisfied, expected value 999999 != 7
    # -> 0.2 + 0.3 + 0.5 * (1/2) = 0.75
    ("runs_wrong", "const_seven", 0.75),
    # parses + imports, crashes at run time -> 0.2
    ("runtime_fail", "const_seven", 0.2),
    # not Python -> 0.0
    ("syntax_error", "const_seven", 0.0),
    # 3-clause task: min_steps=6, required '.map(', value 20 -> all met
    ("perfect", "map_double_sum", 1.0),
    # runs green but 1 step, no .map, wrong value -> 0.2 + 0.3 + 0 = 0.5
    ("runs_wrong", "map_double_sum", 0.5),
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


# A loop-shaped completion: halve 100 until below 10 (100 -> 50 -> 25 ->
# 12.5 -> 6.25 = exactly 4 invocations of `halve`). Exercises repeated
# invocations of the same step, which the checker must count via the
# `<name>_2`, `<name>_3`... invocation-id suffixes.
HALVE_LOOP = """\
from zenml import step, pipeline

@step
def halve(x: float) -> float:
    return x / 2

@pipeline(dynamic=True)
def halve_pipeline():
    value = halve(x=100.0)
    while value.load() >= 10:
        value = halve(x=value)

if __name__ == "__main__":
    halve_pipeline()
"""


def test_step_run_counts_mapped_fanout(tmp_path: Path):
    """step_run_counts sees each mapped invocation (map:<name>:<i> ids)."""
    spec = {
        "step_run_counts": {"double": 4, "numbers": 1, "total": 1},
        "expected_output": {"value": 20},
    }
    result = score(tmp_path, PERFECT["map_double_sum"], spec)
    assert result["reward"] == pytest.approx(1.0), json.dumps(result, indent=2)


def test_step_run_counts_loop(tmp_path: Path):
    """step_run_counts sees loop iterations (<name>_<k> ids)."""
    spec = {
        "step_run_counts": {"halve": 4},
        "expected_output": {"value": 6.25},
    }
    result = score(tmp_path, HALVE_LOOP, spec)
    assert result["reward"] == pytest.approx(1.0), json.dumps(result, indent=2)


def test_step_run_counts_zero_means_branch_not_taken(tmp_path: Path):
    """A count of 0 asserts a step did NOT run (conditional grading)."""
    spec = {"step_run_counts": {"report_even": 0, "halve": 4}}
    result = score(tmp_path, HALVE_LOOP, spec)
    assert result["reward"] == pytest.approx(1.0), json.dumps(result, indent=2)


def test_step_run_counts_wrong_width(tmp_path: Path):
    """A wrong fan-out width fails only that clause: 0.2+0.3+0.5*(1/2)."""
    spec = {
        "step_run_counts": {"double": 3},
        "expected_output": {"value": 20},
    }
    result = score(tmp_path, PERFECT["map_double_sum"], spec)
    assert result["reward"] == pytest.approx(0.75), json.dumps(
        result, indent=2
    )


def test_forbidden_source_bans_hardcoded_answer(tmp_path: Path):
    """forbidden_source fails when the banned literal appears in source."""
    spec = {
        "forbidden_source": ["999999"],
        "expected_output": {"value": 7},
    }
    result = score(tmp_path, RUNS_WRONG, spec)
    # runs green, but both clauses fail -> 0.2 + 0.3 + 0
    assert result["reward"] == pytest.approx(0.5), json.dumps(result, indent=2)
    assert result["spec_clauses"]["forbidden_source"] is False


def test_expected_outputs_each_value_is_a_clause(tmp_path: Path):
    """expected_outputs grades each listed value independently."""
    spec = {"expected_outputs": [20, 999]}
    result = score(tmp_path, PERFECT["map_double_sum"], spec)
    # 20 is the run's total, 999 appears nowhere -> half the spec credit
    assert result["reward"] == pytest.approx(0.75), json.dumps(
        result, indent=2
    )
