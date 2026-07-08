"""Sandbox episode step: execute one generated pipeline and collect its reward."""

import base64
import json
import time
from pathlib import Path
from typing import Any, Dict

from zenml import log_metadata, step
from zenml.client import Client

SCORER_PATH = (
    Path(__file__).resolve().parent.parent
    / "sandbox_scripts"
    / "score_pipeline.py"
)

# Everything the sandbox filesystem needs, keyed by remote filename.
PIPELINE_FILE = "pipeline.py"
SPEC_FILE = "spec.json"
SCORER_FILE = "score_pipeline.py"
REWARD_FILE = "reward.json"


def _put_file(session: Any, content: str, remote_path: str) -> None:
    """Write a text file into the sandbox, whatever the flavor supports.

    The session API defines upload_file, but the local sandbox flavor
    doesn't implement it (BREAKAGE_LOG.md entry 4). Fallback: smuggle the
    content through exec as base64 — ugly, flavor-agnostic, and exactly
    the kind of workaround the spike exists to document.

    Args:
        session: The sandbox session.
        content: File content (text).
        remote_path: Destination path inside the sandbox (relative to the
            session workdir).
    """
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".tmp", delete=False
        ) as f:
            f.write(content)
            local_path = f.name
        session.upload_file(local_path, remote_path)
        return
    except NotImplementedError:
        pass

    encoded = base64.b64encode(content.encode()).decode()
    code = (
        "import base64; "
        f"open({remote_path!r}, 'wb').write(base64.b64decode({encoded!r}))"
    )
    process = session.exec(["python", "-c", code])
    output = process.collect()
    if output.exit_code != 0:
        raise RuntimeError(
            f"base64 upload of {remote_path} failed: {output.stderr[-500:]}"
        )


def _get_file(session: Any, remote_path: str) -> str:
    """Read a text file out of the sandbox (same fallback story as _put_file).

    Args:
        session: The sandbox session.
        remote_path: Path inside the sandbox.

    Returns:
        File content.

    Raises:
        RuntimeError: If the file cannot be read.
    """
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            local_path = f.name
        session.download_file(remote_path, local_path)
        return Path(local_path).read_text()
    except NotImplementedError:
        pass

    code = (
        "import base64, sys; "
        f"sys.stdout.write(base64.b64encode(open({remote_path!r}, 'rb')"
        ".read()).decode())"
    )
    process = session.exec(["python", "-c", code])
    output = process.collect()
    if output.exit_code != 0:
        raise RuntimeError(
            f"base64 download of {remote_path} failed: {output.stderr[-500:]}"
        )
    return base64.b64decode(output.stdout.strip()).decode()


@step
def run_episode(episode: Dict[str, Any]) -> Dict[str, Any]:
    """Run one generated pipeline inside a sandbox and score it.

    Never raises: dynamic pipelines have no CONTINUE_ON_FAILURE, so one
    crashed episode step would abort the whole training run. Any failure
    here (sandbox creation, upload, execution, scoring) becomes
    reward=0.0 with the error recorded on the episode — for RL purposes a
    broken episode and a bad completion are the same thing: zero reward.

    Args:
        episode: Episode dict from generate_rollouts.

    Returns:
        The episode enriched with reward, reward_breakdown, error, and
        timing fields.
    """
    timings: Dict[str, float] = {}
    result: Dict[str, Any] = {
        **episode,
        "reward": 0.0,
        "reward_breakdown": {},
        "spec_clauses": {},
        "error": None,
    }

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
            _put_file(session, episode["completion_text"], PIPELINE_FILE)
            _put_file(session, json.dumps(episode["spec"]), SPEC_FILE)
            _put_file(session, SCORER_PATH.read_text(), SCORER_FILE)
            timings["upload_s"] = round(time.time() - started, 2)

            started = time.time()
            process = session.exec(
                ["python", SCORER_FILE, PIPELINE_FILE, SPEC_FILE, REWARD_FILE]
            )
            # collect() has no timeout parameter; the overall wall-clock
            # cap lives inside the scorer (RUN_TIMEOUT_SECONDS on each of
            # its subprocesses).
            output = process.collect()
            timings["score_exec_s"] = round(time.time() - started, 2)

            if output.exit_code != 0:
                raise RuntimeError(
                    f"scorer exited {output.exit_code}: "
                    f"{(output.stderr or output.stdout)[-800:]}"
                )

            reward_data = json.loads(_get_file(session, REWARD_FILE))

        result["reward"] = reward_data["reward"]
        result["reward_breakdown"] = reward_data["breakdown"]
        result["spec_clauses"] = reward_data.get("spec_clauses", {})
        result["error"] = reward_data.get("error")
        timings.update(
            {
                f"scorer_{key}": value
                for key, value in reward_data.get("timings", {}).items()
            }
        )
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    result["timings"] = timings
    log_metadata(
        metadata={
            "task_id": episode.get("task_id", "?"),
            "rollout_index": episode.get("rollout_index", -1),
            "reward": result["reward"],
            "error": result["error"] or "",
            **{k: v for k, v in timings.items()},
        }
    )
    return result
