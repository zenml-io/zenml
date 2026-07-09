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
    import os
    import tempfile

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
    except Exception:
        # The session filesystem API has no workdir contract (BREAKAGE_LOG
        # entry 18): relative remote paths work on the kubernetes flavor
        # but Modal's copy_from_local rejects them. The base64 transport
        # below writes relative to the exec cwd on every flavor, which is
        # also what keeps parallel local sessions isolated — so fall back
        # rather than switching to absolute paths.
        pass
    finally:
        if local_path:
            os.unlink(local_path)

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
    import os
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            local_path = f.name
        session.download_file(remote_path, local_path)
        content = Path(local_path).read_text()
        os.unlink(local_path)
        return content
    except NotImplementedError:
        os.unlink(local_path)
    except Exception:
        # Same workdir-contract fallback as _put_file (entry 18).
        os.unlink(local_path)

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


def _snapshot_failed_session(
    session: Any, result: Dict[str, Any], timings: Dict[str, float]
) -> None:
    """Best-effort filesystem snapshot of a failed episode's sandbox.

    Must run INSIDE the session context manager: the sessions are created
    with destroy_on_exit=True, so by the time a failure propagates out of
    the with-block the filesystem is gone. Never raises — a snapshot
    failure must not turn a scored episode into a crashed step. Flavors
    without snapshot support (kubernetes, local — only Modal implements
    it today) land in `snapshot_error` so the support gap is visible in
    the episode record instead of silently absent.

    Args:
        session: The (still open) sandbox session.
        result: Episode result dict, mutated with snapshot/snapshot_error.
        timings: Timing dict, mutated with snapshot_s.
    """
    started = time.time()
    try:
        snapshot = session.create_snapshot()
        result["snapshot"] = snapshot.model_dump(mode="json")
    except NotImplementedError as e:
        result["snapshot_error"] = f"unsupported: {e}"
    except Exception as e:
        result["snapshot_error"] = f"{type(e).__name__}: {e}"
    timings["snapshot_s"] = round(time.time() - started, 2)


@step
def run_episode(
    episode: Dict[str, Any], snapshot_on_failure: bool = False
) -> Dict[str, Any]:
    """Run one generated pipeline inside a sandbox and score it.

    Never raises: dynamic pipelines have no CONTINUE_ON_FAILURE, so one
    crashed episode step would abort the whole training run. Any failure
    here (sandbox creation, upload, execution, scoring) becomes
    reward=0.0 with the error recorded on the episode — for RL purposes a
    broken episode and a bad completion are the same thing: zero reward.

    Args:
        episode: Episode dict from generate_rollouts.
        snapshot_on_failure: If True, snapshot the sandbox filesystem
            before it is destroyed whenever the episode fails (scorer
            error or infra error), and record the snapshot reference on
            the episode. Restore later with restore_sandbox.py. The
            motivating incident is BREAKAGE_LOG entry 16: hours of
            artifact archaeology to learn that "reward 0.0" meant "the
            node had no disk" — a snapshot answers that in one look.

    Returns:
        The episode enriched with reward, reward_breakdown, error,
        snapshot, and timing fields.
    """
    timings: Dict[str, float] = {}
    # `error` = the scorer's verdict on the generated code (a bad
    # completion earning 0.0 is EXPECTED and healthy). `infra_error` =
    # this step itself broke (sandbox, upload, scorer crash) — the reward
    # is 0.0 either way, but only infra_error means the harness is sick.
    result: Dict[str, Any] = {
        **episode,
        "reward": 0.0,
        "reward_breakdown": {},
        "spec_clauses": {},
        "error": None,
        "infra_error": None,
        "snapshot": None,
        "snapshot_error": None,
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

            # The failure paths must snapshot INSIDE this block: on exit
            # the session is destroyed and the filesystem with it.
            try:
                started = time.time()
                # program_text = fence-stripped completion; falls back to
                # the raw text for episodes produced before the field
                # existed.
                _put_file(
                    session,
                    episode.get("program_text", episode["completion_text"]),
                    PIPELINE_FILE,
                )
                _put_file(session, json.dumps(episode["spec"]), SPEC_FILE)
                _put_file(session, SCORER_PATH.read_text(), SCORER_FILE)
                timings["upload_s"] = round(time.time() - started, 2)

                started = time.time()
                process = session.exec(
                    [
                        "python",
                        SCORER_FILE,
                        PIPELINE_FILE,
                        SPEC_FILE,
                        REWARD_FILE,
                    ]
                )
                # collect() has no timeout parameter; the overall
                # wall-clock cap lives inside the scorer
                # (RUN_TIMEOUT_SECONDS on each of its subprocesses).
                output = process.collect()
                timings["score_exec_s"] = round(time.time() - started, 2)

                if output.exit_code != 0:
                    raise RuntimeError(
                        f"scorer exited {output.exit_code}: "
                        f"{(output.stderr or output.stdout)[-800:]}"
                    )

                reward_data = json.loads(_get_file(session, REWARD_FILE))
            except Exception:
                if snapshot_on_failure:
                    _snapshot_failed_session(session, result, timings)
                raise

            if snapshot_on_failure and reward_data.get("error"):
                _snapshot_failed_session(session, result, timings)

        result["reward"] = reward_data["reward"]
        result["reward_breakdown"] = reward_data["breakdown"]
        result["spec_clauses"] = reward_data.get("spec_clauses", {})
        result["error"] = reward_data.get("error")
        # The generated pipeline's own stdout/stderr tail — without it,
        # "pipeline exited nonzero" is undiagnosable (Stage 3 lesson).
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
    log_metadata(
        metadata={
            "task_id": episode.get("task_id", "?"),
            "rollout_index": episode.get("rollout_index", -1),
            "reward": result["reward"],
            "error": result["error"] or "",
            "infra_error": result["infra_error"] or "",
            "snapshot_ref": (result["snapshot"] or {}).get("ref", ""),
            "snapshot_error": result["snapshot_error"] or "",
            **{k: v for k, v in timings.items()},
        }
    )
    return result
