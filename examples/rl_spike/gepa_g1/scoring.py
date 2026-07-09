"""Sandbox scoring with the slim GEPA contract: program text in, reward JSON out.

Reuses the parent example's assets read-only: the in-sandbox scorer
(sandbox_scripts/score_pipeline.py, uploaded verbatim — the verifier is
byte-identical to the GRPO baseline's, which is the whole point of the
loop-genericity question) and run_episode's flavor-agnostic file
transport helpers. None of the GRPO episode fields (token IDs, logprobs)
exist here; GEPA needs only text and a reward.
"""

import json
import time
from typing import Any, Dict

from reuse import load_rl_spike_module

# Private-helper reuse across sibling example dirs, accepted for the spike:
# copying the 90-line flavor-fallback transport would fork the workaround
# documented in BREAKAGE_LOG entries 4/18.
_run_episode = load_rl_spike_module("steps/run_episode.py")
PIPELINE_FILE = _run_episode.PIPELINE_FILE
REWARD_FILE = _run_episode.REWARD_FILE
SCORER_FILE = _run_episode.SCORER_FILE
SCORER_PATH = _run_episode.SCORER_PATH
SPEC_FILE = _run_episode.SPEC_FILE
_get_file = _run_episode._get_file
_put_file = _run_episode._put_file


def score_program(program_text: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Run one generated pipeline in a fresh sandbox session and score it.

    Mirrors run_episode's never-raise rule, which is also gepa's adapter
    contract ("never raise for individual example failures"): any infra
    failure becomes reward 0.0 with the error recorded, so one broken
    sandbox can't abort an optimization run.

    Args:
        program_text: Fence-stripped Python source to execute and score.
        spec: The task's declarative spec (tasks.jsonl `spec` field).

    Returns:
        Dict with reward, breakdown, spec_clauses, error, run_output_tail,
        infra_error, and timings — the scorer's reward JSON plus harness
        health fields.
    """
    from zenml.client import Client

    result: Dict[str, Any] = {
        "reward": 0.0,
        "breakdown": {},
        "spec_clauses": {},
        "error": None,
        "run_output_tail": "",
        "infra_error": None,
        "timings": {},
    }
    timings: Dict[str, float] = {}

    try:
        sandbox = Client().active_stack.sandbox
        if sandbox is None:
            raise RuntimeError(
                "The active stack has no sandbox component. Register one, "
                "e.g.: `zenml sandbox register local_sandbox --flavor=local` "
                "and add it to the stack."
            )

        started = time.time()
        with sandbox.create_session(destroy_on_exit=True) as session:
            timings["session_create_s"] = round(time.time() - started, 2)

            started = time.time()
            _put_file(session, program_text, PIPELINE_FILE)
            _put_file(session, json.dumps(spec), SPEC_FILE)
            _put_file(session, SCORER_PATH.read_text(), SCORER_FILE)
            timings["upload_s"] = round(time.time() - started, 2)

            started = time.time()
            process = session.exec(
                ["python", SCORER_FILE, PIPELINE_FILE, SPEC_FILE, REWARD_FILE]
            )
            output = process.collect()
            timings["score_exec_s"] = round(time.time() - started, 2)

            if output.exit_code != 0:
                raise RuntimeError(
                    f"scorer exited {output.exit_code}: "
                    f"{(output.stderr or output.stdout)[-800:]}"
                )
            reward_data = json.loads(_get_file(session, REWARD_FILE))

        result["reward"] = reward_data["reward"]
        result["breakdown"] = reward_data["breakdown"]
        result["spec_clauses"] = reward_data.get("spec_clauses", {})
        result["error"] = reward_data.get("error")
        result["run_output_tail"] = reward_data.get("run_output_tail", "")
        timings.update(
            {
                f"scorer_{key}": value
                for key, value in reward_data.get("timings", {}).items()
            }
        )
    except Exception as e:
        result["infra_error"] = f"{type(e).__name__}: {e}"

    result["timings"] = timings
    return result
