"""In-sandbox scorer: run a generated ZenML pipeline and compute its reward.

This file is uploaded into every sandbox session and executed there — it is
deliberately self-contained (stdlib + zenml only, no imports from the
example package) because the sandbox filesystem only contains what
`run_episode` uploads.

Usage (inside the sandbox):

    python score_pipeline.py <pipeline.py> <spec.json> <reward.json>

The scorer sets ZENML_CONFIG_PATH to a fresh temp directory before any
zenml import, so the generated pipeline runs against a throwaway local
sqlite store. This matters most on the LOCAL sandbox flavor, which is a
bare subprocess forwarding HOME from the host: without the override, the
generated pipeline would find the host's ~/.config/zenml and create junk
runs on whatever server the host is logged into (in this repo's case, the
staging Pro server). Subprocesses inherit the override via the
environment.

Reward (0-1), mirroring PLAN.md:
    +0.3  the file parses (ast) AND imports cleanly (module top-level runs)
    +0.4  executing the file completes with exit code 0 AND a completed
          pipeline run exists in the local store
    +0.3  declarative spec clauses, partial credit per clause:
          - min_steps:        the run has at least N step runs
          - required_api:     every listed substring appears in the source
          - expected_output:  some output artifact of the run equals the value
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import time

# Isolate BEFORE any zenml import anywhere in this process: zenml reads
# ZENML_CONFIG_PATH at import/client-init time.
os.environ["ZENML_CONFIG_PATH"] = tempfile.mkdtemp(prefix="rl-spike-store-")
os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
os.environ["AUTO_OPEN_DASHBOARD"] = "false"
os.environ["ZENML_ENABLE_RICH_TRACEBACK"] = "false"
os.environ["ZENML_LOGGING_VERBOSITY"] = "WARN"

PARSE_IMPORT_REWARD = 0.3
RUNS_GREEN_REWARD = 0.4
SPEC_REWARD = 0.3

# Generous ceiling for toy pipelines: local sqlite init dominates, the
# pipelines themselves are trivial arithmetic.
RUN_TIMEOUT_SECONDS = 600


def check_parse(source: str) -> "str | None":
    """Concrete parse error, or None if the source is valid Python."""
    try:
        ast.parse(source)
        return None
    except SyntaxError as error:
        return f"SyntaxError: {error.msg} (line {error.lineno})"


def check_import(pipeline_file: str) -> "str | None":
    """Concrete import error, or None if the module imports cleanly.

    Runs in a subprocess so a hostile or broken module can't take the
    scorer down with it. The __main__ guard means importing does NOT run
    the pipeline — it only executes decorators and module-level code.
    """
    code = (
        "import importlib.util as u, sys\n"
        f"spec = u.spec_from_file_location('generated_pipeline', {pipeline_file!r})\n"
        "m = u.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_SECONDS,
    )
    if result.returncode == 0:
        return None
    return (result.stderr or result.stdout or "import failed").strip()[-800:]


def run_pipeline_file(pipeline_file: str) -> "tuple[bool, str]":
    """Execute the generated file; True if it exits 0.

    Returns:
        (success, tail of combined output for the episode log).
    """
    try:
        result = subprocess.run(
            [sys.executable, pipeline_file],
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {RUN_TIMEOUT_SECONDS}s"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output[-4000:]


def get_latest_completed_run():
    """Fetch the most recent completed pipeline run from the local store.

    Returns None if there is no completed run — which means the generated
    file exited 0 without actually running a pipeline (e.g. it just
    printed something), so it must not earn the runs-green reward.
    """
    from zenml.client import Client
    from zenml.enums import ExecutionStatus

    runs = Client().list_pipeline_runs(
        sort_by="desc:created", size=5, hydrate=True
    )
    for run in runs.items:
        if run.status == ExecutionStatus.COMPLETED:
            return run
    return None


def iter_output_values(run):
    """Yield every output artifact value of every step in the run.

    Artifact loading can fail for exotic return types; those artifacts are
    skipped rather than failing the whole spec check.
    """
    for step in run.steps.values():
        for artifact_versions in step.outputs.values():
            for artifact_version in artifact_versions:
                try:
                    yield artifact_version.load()
                except Exception:
                    continue


def values_equal(expected, actual) -> bool:
    """Spec-value equality with two deliberate strictness rules.

    - bools only match bools (in plain Python, True == 1 — a pipeline
      returning 1 must not satisfy an expected value of True).
    - tuples count as lists (a step returning (1, 2) satisfies [1, 2];
      JSON specs cannot express tuples).
    """
    if isinstance(expected, bool) or isinstance(actual, bool):
        return (
            isinstance(expected, bool)
            and isinstance(actual, bool)
            and expected == actual
        )
    if isinstance(actual, tuple):
        actual = list(actual)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            values_equal(e, a) for e, a in zip(expected, actual)
        )
    try:
        return bool(expected == actual)
    except Exception:
        return False


def check_spec(spec: dict, source: str, run) -> "tuple[float, dict]":
    """Score the declarative spec clauses; each clause weighs equally.

    Returns:
        (fraction of SPEC_REWARD earned, per-clause breakdown).
    """
    clauses = {}
    if "min_steps" in spec:
        clauses["min_steps"] = (
            run is not None and len(run.steps) >= spec["min_steps"]
        )
    if "required_api" in spec:
        clauses["required_api"] = all(
            substring in source for substring in spec["required_api"]
        )
    if "expected_output" in spec:
        expected = spec["expected_output"]["value"]
        clauses["expected_output"] = run is not None and any(
            values_equal(expected, value) for value in iter_output_values(run)
        )
    if not clauses:
        return 0.0, {}
    fraction = sum(clauses.values()) / len(clauses)
    return fraction, clauses


def main() -> None:
    """Score sys.argv[1] against sys.argv[2], writing sys.argv[3]."""
    pipeline_file, spec_file, reward_file = sys.argv[1:4]

    with open(pipeline_file) as f:
        source = f.read()
    with open(spec_file) as f:
        spec = json.load(f)

    result = {
        "reward": 0.0,
        "breakdown": {
            "parse_import": 0.0,
            "runs_green": 0.0,
            "spec": 0.0,
        },
        "spec_clauses": {},
        "timings": {},
        "error": None,
    }

    started = time.time()
    parse_error = check_parse(source)
    import_error = (
        check_import(pipeline_file) if parse_error is None else None
    )
    result["timings"]["parse_import_s"] = round(time.time() - started, 2)

    if parse_error is not None or import_error is not None:
        result["error"] = parse_error or import_error
        _write(reward_file, result)
        return
    result["breakdown"]["parse_import"] = PARSE_IMPORT_REWARD

    started = time.time()
    ran_green, run_output = run_pipeline_file(pipeline_file)
    result["timings"]["pipeline_run_s"] = round(time.time() - started, 2)
    result["run_output_tail"] = run_output[-1500:]

    started = time.time()
    run = get_latest_completed_run() if ran_green else None
    result["timings"]["store_query_s"] = round(time.time() - started, 2)

    if ran_green and run is not None:
        result["breakdown"]["runs_green"] = RUNS_GREEN_REWARD
    else:
        result["error"] = (
            "pipeline exited nonzero"
            if not ran_green
            else "exit 0 but no completed run in store"
        )

    # Spec checks run even when the pipeline failed: required_api is a
    # source-level clause a failed pipeline can still legitimately earn,
    # and partial signal is better gradient than a cliff.
    started = time.time()
    fraction, clauses = check_spec(spec, source, run)
    result["timings"]["spec_check_s"] = round(time.time() - started, 2)
    result["breakdown"]["spec"] = round(SPEC_REWARD * fraction, 4)
    result["spec_clauses"] = clauses

    result["reward"] = round(sum(result["breakdown"].values()), 4)
    _write(reward_file, result)


def _write(reward_file: str, result: dict) -> None:
    with open(reward_file, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"reward": result["reward"], "error": result["error"]}))


if __name__ == "__main__":
    main()
