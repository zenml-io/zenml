"""Fetch, verify, build, and qualify the fixed ten-task pilot dataset."""

import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from runtime.docker_env import DockerEnvironment
from runtime.grading import grade_environment

TASK_MANIFEST = Path(__file__).parent / "tasks.json"


def sha256(path: Path) -> str:
    """Hash the exact bytes of a task file.

    Args:
        path: File to hash.

    Returns:
        Lowercase SHA-256 digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_task(
    task: dict[str, Any], directory: Path, revision: str
) -> None:
    """Download only pinned, reviewed files and verify their hashes.

    Args:
        task: Task ID and expected file hashes.
        directory: Local directory for this task.
        revision: Pinned Hugging Face dataset revision.

    Raises:
        ValueError: A downloaded or existing file differs from its pinned hash.
    """
    for relative, expected in task["task_file_sha256"].items():
        path = directory / relative
        if path.exists():
            if sha256(path) != expected:
                raise ValueError(f"Task file hash mismatch: {path}")
            continue
        url = (
            "https://huggingface.co/datasets/obiwan96/endless-terminals/resolve/"
            f"{revision}/{task['task_id']}/{relative}"
        )
        with urlopen(url, timeout=30) as response:
            data = response.read(2_000_001)
        if (
            len(data) > 2_000_000
            or hashlib.sha256(data).hexdigest() != expected
        ):
            raise ValueError(f"Downloaded task hash mismatch: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def task_image(task: dict[str, Any], directory: Path) -> str:
    """Reuse a known local image or build the pinned task Dockerfile.

    Args:
        task: Task identity and optional previously qualified local image ID.
        directory: Verified task directory.

    Returns:
        The immutable local AMD64 image ID.

    Raises:
        RuntimeError: Docker is unavailable or the build fails.
    """
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker must be installed and running")
    preferred = task.get("qualified_image_id")
    if preferred:
        existing = subprocess.run(
            [docker, "image", "inspect", preferred],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if existing.returncode == 0:
            details = json.loads(existing.stdout)[0]
            if details["Architecture"] == "amd64" and details["Os"] == "linux":
                return str(details["Id"])
    tag = f"endless-example:{task['task_id']}"
    with (directory / "build.log").open("w") as log:
        build = subprocess.run(
            [
                docker,
                "build",
                "--platform",
                "linux/amd64",
                "-t",
                tag,
                str(directory / "environment"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=600,
            check=False,
        )
    if build.returncode:
        raise RuntimeError(
            f"Task image build failed; inspect {directory / 'build.log'}"
        )
    return subprocess.check_output(
        [docker, "image", "inspect", "--format", "{{.Id}}", tag],
        text=True,
        timeout=30,
    ).strip()


def qualify_task(task: dict[str, Any], directory: Path) -> dict[str, Any]:
    """Check initial state, reference success, and unsolved/corrupted rejection.

    Args:
        task: Task with a resolved immutable image and source guards.
        directory: Verified task files.

    Returns:
        Structured qualification results from fresh isolated containers.

    Raises:
        RuntimeError: A task does not meet the qualification contract.
    """
    results = {}
    probe = task.get("corrupted_output_probe")
    if (
        not probe
        or not probe.startswith("/home/user/")
        or ".." in Path(probe).parts
    ):
        raise RuntimeError(
            "Qualification requires a corruption probe inside /home/user"
        )
    for phase in ("initial", "noop", "reference", "corrupted"):
        with DockerEnvironment(
            task["local_image_id"], command_timeout=30
        ) as env:
            if phase in ("reference", "corrupted"):
                success, output = env.execute(
                    (directory / "solution/solve.sh").read_text()
                )
                if not success:
                    raise RuntimeError(
                        f"Reference command failed: {output[:1000]}"
                    )
            if phase == "corrupted":
                command = "printf 'INVALID_OUTPUT\\n' > " + shlex.quote(probe)
                success, output = env.execute(command)
                if not success:
                    raise RuntimeError(
                        f"Output corruption failed: {output[:1000]}"
                    )
            test = directory / (
                "environment/test_initial_state.py"
                if phase == "initial"
                else "tests/test_final_state.py"
            )
            grade = grade_environment(
                env, test, task.get("protected_sources", {})
            )
            expected = phase in ("initial", "reference")
            if (
                grade.get("infrastructure_error")
                or grade["audited_valid"] != expected
            ):
                raise RuntimeError(
                    f"{task['task_id']} failed {phase} qualification: {grade}"
                )
            if not expected and (
                grade["raw_reward"] != 0
                or not grade["test_counts"]["failure"]
                or grade["test_counts"]["skipped"]
                or grade["test_counts"]["error"]
                or not all(
                    source.get("unchanged") is True
                    for source in grade.get("protected_sources", {}).values()
                )
            ):
                raise RuntimeError(
                    f"{phase} state did not produce valid failing tests"
                )
            results[phase] = grade
    return results


def prepare_tasks(
    data_directory: Path, selected_ids: list[str]
) -> dict[str, Any]:
    """Prepare the selected tasks for a real pipeline evaluation.

    Args:
        data_directory: Persistent local task cache.
        selected_ids: Explicit subset, or empty for all ten reviewed tasks.

    Returns:
        Pinned task and image identities with fresh CPU qualification evidence.

    Raises:
        ValueError: A selected task is outside the reviewed pilot subset.
    """
    manifest = json.loads(TASK_MANIFEST.read_text())
    known = {task["task_id"]: task for task in manifest["tasks"]}
    if set(selected_ids) - known.keys():
        raise ValueError("Only task IDs in tasks.json may be evaluated")
    tasks = []
    for task_id in selected_ids or list(known):
        task = dict(known[task_id])
        directory = data_directory / task_id
        download_task(task, directory, manifest["dataset_revision"])
        task["local_image_id"] = task_image(task, directory)
        task["qualification"] = qualify_task(task, directory)
        tasks.append(task)
    return {"dataset_revision": manifest["dataset_revision"], "tasks": tasks}
