"""Pure bounded episodes that return complete JSON artifact evidence."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from .contract import SYSTEM_MESSAGE, UPSTREAM_COMMIT, extract_action
from .docker_env import DockerEnvironment
from .environment import TerminalEnvironment
from .grading import grade_environment
from .models import Model

ROOT = Path(__file__).resolve().parent
MAX_OUTPUT = 50_000


def verify_task_files(task: dict[str, Any], directory: Path) -> None:
    """Reject changed, missing, or escaped task files before starting a sandbox.

    Args:
        task: Manifest entry containing task_file_sha256.
        directory: Root of this task's files.

    Raises:
        ValueError: A required file is absent or a hash/path is invalid.
    """
    hashes = task["task_file_sha256"]
    if not {"instruction.md", "tests/test_final_state.py"} <= hashes.keys():
        raise ValueError("Instruction and final grader hashes are required")
    for relative, expected in hashes.items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("Task file escapes its directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Task file hash mismatch: {relative}")


def run_episode(
    task: dict[str, Any],
    task_directory: Path,
    model: Model,
    output: Path,
    *,
    identity: dict[str, Any],
    system_message: str = SYSTEM_MESSAGE,
    max_actions: int = 16,
    command_timeout: float = 10,
    episode_timeout: float = 180,
    environment_factory: Callable[[str, float, float], TerminalEnvironment]
    | None = None,
) -> dict[str, Any]:
    """Run an episode, save evidence even on failure, and remove sandboxes.

    Args:
        task: Manifest entry with immutable image ID and task file hashes.
        task_directory: Directory containing the instruction and hidden tests.
        model: Scripted fixture or explicitly configured model endpoint.
        output: New result directory; existing paths are rejected.
        identity: Model/fixture provenance recorded with the episode.
        system_message: Exact system prompt sent to the model and hashed in evidence.
        max_actions: Maximum model turns, including invalid responses.
        command_timeout: Maximum seconds for a terminal command.
        episode_timeout: Agent interaction budget in seconds. Grading has a
            separate 120-second limit; Docker setup and cleanup are bounded.
        environment_factory: Optional sandbox constructor receiving immutable
            image reference, command timeout, and interaction timeout.

    Returns:
        Result manifest, including audited grading or infrastructure error.
        Ordinary model, terminal, and grading errors are captured in this result.

    Raises:
        ValueError: The prompt is blank or limits/task-file integrity are invalid.
        FileExistsError: The output directory already exists.
        BaseException: Interruptions propagate after cleanup and evidence writes.
    """  # noqa: DOC503
    if not system_message.strip():
        raise ValueError("system_message must not be blank")
    if (
        not 1 <= max_actions <= 16
        or not 0 < command_timeout <= 90
        or not 0 < episode_timeout <= 1200
    ):
        raise ValueError("Limits must fit the bounded pilot envelope")
    entry = task
    task_id = task["task_id"]
    verify_task_files(task, task_directory)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    messages = [
        {"role": "system", "content": system_message},
        {
            "role": "user",
            "content": (task_directory / "instruction.md").read_text(),
        },
    ]
    result: dict[str, Any] = {
        "task_id": task_id,
        "image_id": entry.get("image_ref") or entry["local_image_id"],
        "runtime": "sandbox" if environment_factory is not None else "docker",
        "identity": identity,
        "upstream_commit": UPSTREAM_COMMIT,
        "system_prompt_sha256": hashlib.sha256(
            system_message.encode()
        ).hexdigest(),
        "dataset_revision": task.get("dataset_revision"),
        "limits": {
            "max_actions": max_actions,
            "command_timeout": command_timeout,
            "episode_timeout": episode_timeout,
        },
        "turns": [],
        "exit_reason": "not_started",
        "grading": None,
    }
    result["adapter_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "runner.py",
            "docker_env.py",
            "docker_command.py",
            "docker_grading.py",
            "environment.py",
            "grading.py",
            "models.py",
            "http_client.py",
            "contract.py",
        )
    }
    if environment_factory is not None:
        result["adapter_sha256"].update(
            {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in ROOT.glob("sandbox_*.py")
            }
        )
    env: TerminalEnvironment | None = None
    try:
        env = (
            environment_factory(
                result["image_id"], command_timeout, episode_timeout
            )
            if environment_factory is not None
            else DockerEnvironment(
                entry["local_image_id"],
                command_timeout=command_timeout,
                episode_timeout=episode_timeout,
            )
        )
        with env:
            result["container_id"] = env.container_id
            result["environment"] = env.provenance
            interaction_started = time.monotonic()
            (output / "result.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
            protected = dict(entry.get("protected_sources", {}))
            source = entry.get("mutation", {}).get("protected_source")
            if source:
                protected[source] = entry["mutation_evidence"]["source_sha256"]
            for source, expected in protected.items():
                if env.source_hash(source) != expected:
                    raise RuntimeError(
                        "Initial protected source differs from qualified image"
                    )
            for turn in range(max_actions):
                remaining = episode_timeout - (
                    time.monotonic() - interaction_started
                )
                if remaining <= 0:
                    raise TimeoutError("Episode deadline exceeded")
                response, usage = model.complete(
                    messages, timeout=min(remaining, 120)
                )
                if time.monotonic() - interaction_started >= episode_timeout:
                    raise TimeoutError(
                        "Episode deadline exceeded during model request"
                    )
                action = extract_action(response)
                messages.append({"role": "assistant", "content": response})
                event = {"turn": turn + 1, "action": action, "usage": usage}
                result["turns"].append(event)
                if action["type"] == "done":
                    result["exit_reason"] = "done"
                    break
                if action["type"] == "invalid":
                    observation = "Could not parse a single <command>...</command> or <action>done</action>. Please respond with exactly one of those."
                else:
                    success, terminal = env.execute(action["command"] or "")
                    truncated = ""
                    if len(terminal) > MAX_OUTPUT:
                        terminal = terminal[:MAX_OUTPUT]
                        # Retain the upstream formatting, including its reported length.
                        truncated = f"\n[Output truncated: showing first {MAX_OUTPUT} of {len(terminal)} characters]"
                    observation = f"Command {'executed successfully' if success else 'failed'}. Output: {terminal}{truncated}\n\n(exit_code={0 if success else 1})"
                messages.append({"role": "user", "content": observation})
                (output / "transcript.json").write_text(
                    json.dumps(messages, indent=2) + "\n"
                )
                if env.stopped:
                    result["exit_reason"] = "terminal_stopped"
                    break
            else:
                result["exit_reason"] = "max_actions"
            result["grading"] = grade_environment(
                env,
                task_directory / "tests" / "test_final_state.py",
                protected,
            )
            if result["grading"].get("infrastructure_error"):
                result["exit_reason"] = "infrastructure_error"
    except Exception as exc:
        result["exit_reason"] = "infrastructure_error"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    except BaseException:
        result["exit_reason"] = "interrupted"
        raise
    finally:
        result["transcript"] = messages
        result["cleanup_complete"] = bool(env is not None and env.closed)
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (output / "transcript.json").write_text(
            json.dumps(messages, indent=2) + "\n"
        )
        (output / "result.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
    return result
