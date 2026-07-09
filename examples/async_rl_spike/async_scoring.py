"""Sandbox scoring for the rollout pipeline.

Runs one generated pipeline per episode inside a sandbox session and
attaches its reward, using the shared in-sandbox scorer.
"""

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from zenml.client import Client

SCORER_PATH = (
    Path(__file__).resolve().parent / "sandbox_scripts" / "score_pipeline.py"
)
SCORER_SRC = SCORER_PATH.read_text()
PIPELINE_FILE = "/tmp/pipeline.py"
SPEC_FILE = "/tmp/spec.json"
SCORER_FILE = "/tmp/score_pipeline.py"
REWARD_FILE = "/tmp/reward.json"


def _put_file(session: Any, content: str, remote_path: str) -> None:
    """Write a text file into the sandbox, whatever the flavor supports.

    The local sandbox flavor does not implement upload_file, so this falls
    back to smuggling the content through exec as base64.

    Args:
        session: The sandbox session.
        content: File content.
        remote_path: Destination path inside the sandbox.

    Raises:
        RuntimeError: If the base64 fallback write fails.
    """
    local_path = None
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
    finally:
        if local_path:
            os.unlink(local_path)

    encoded = base64.b64encode(content.encode()).decode()
    code = (
        "import base64; "
        f"open({remote_path!r}, 'wb').write(base64.b64decode({encoded!r}))"
    )
    output = session.exec(["python", "-c", code]).collect()
    if output.exit_code != 0:
        raise RuntimeError(
            f"base64 upload of {remote_path} failed: {output.stderr[-500:]}"
        )


def _get_file(session: Any, remote_path: str) -> str:
    """Read a text file out of the sandbox (same fallback as _put_file).

    Args:
        session: The sandbox session.
        remote_path: Path inside the sandbox.

    Raises:
        RuntimeError: If the file cannot be read.

    Returns:
        File content.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            local_path = f.name
        session.download_file(remote_path, local_path)
        content = Path(local_path).read_text()
        os.unlink(local_path)
        return content
    except NotImplementedError:
        os.unlink(local_path)

    code = (
        "import base64, sys; "
        f"sys.stdout.write(base64.b64encode(open({remote_path!r}, 'rb')"
        ".read()).decode())"
    )
    output = session.exec(["python", "-c", code]).collect()
    if output.exit_code != 0:
        raise RuntimeError(
            f"base64 download of {remote_path} failed: {output.stderr[-500:]}"
        )
    return base64.b64decode(output.stdout.strip()).decode()


def score_one(episode: Dict[str, Any]) -> Dict[str, Any]:
    """Run one generated pipeline in a sandbox and attach its reward.

    Never raises: any failure becomes reward 0.0 with the error recorded,
    so one bad episode cannot abort the generator step.

    Args:
        episode: Episode record from a generator.

    Returns:
        The episode enriched with reward, reward_breakdown, error, and
        infra_error fields.
    """
    result: Dict[str, Any] = {
        **episode,
        "reward": 0.0,
        "reward_breakdown": {},
        "spec_clauses": {},
        "error": None,
        "infra_error": None,
    }
    timings: Dict[str, float] = {}
    try:
        sandbox = Client().active_stack.sandbox
        if sandbox is None:
            raise RuntimeError("The active stack has no sandbox component.")

        with sandbox.create_session(destroy_on_exit=True) as session:
            started = time.time()
            _put_file(
                session,
                episode.get("program_text", episode["completion_text"]),
                PIPELINE_FILE,
            )
            _put_file(session, json.dumps(episode["spec"]), SPEC_FILE)
            _put_file(session, SCORER_SRC, SCORER_FILE)
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
        result["reward_breakdown"] = reward_data["breakdown"]
        result["spec_clauses"] = reward_data.get("spec_clauses", {})
        result["error"] = reward_data.get("error")
    except Exception as e:
        result["infra_error"] = f"{type(e).__name__}: {e}"

    result["timings"] = timings
    return result


def score_group(episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score every episode in a group.

    Args:
        episodes: The group's episode records.

    Returns:
        The scored episodes.
    """
    return [score_one(episode) for episode in episodes]
