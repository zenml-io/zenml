"""Docker transport for a clean verifier, separate from grading semantics."""

import io
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .docker_env import DockerEnvironment


def verify_snapshot(
    env: "DockerEnvironment", archive: bytes, test_path: Path
) -> tuple[int, str, bytes]:
    """Load task data and hidden tests into a fresh Docker container.

    Args:
        env: Environment tracking all containers for cleanup.
        archive: Validated task-home archive.
        test_path: Trusted verifier source.

    Returns:
        Pytest exit code, output, and JUnit XML bytes.

    Raises:
        RuntimeError: Verifier execution or cleanup fails.
    """  # noqa: DOC502
    verifier = env.create_container()
    try:
        env.run_docker(
            [
                "exec",
                "--workdir",
                "/",
                verifier,
                "/bin/rm",
                "-rf",
                "/home/user",
            ]
        )
        env.run_docker(
            [
                "exec",
                "--workdir",
                "/",
                verifier,
                "/bin/mkdir",
                "-p",
                "/home/user",
                "/opt/endless-grader",
            ]
        )
        env.run_docker(
            ["cp", "-", f"{verifier}:/home/user"], input_data=archive
        )
        env.run_docker(
            [
                "cp",
                str(test_path.resolve()),
                f"{verifier}:/opt/endless-grader/test_final_state.py",
            ]
        )
        completed = env.run_docker(
            [
                "exec",
                "--workdir",
                "/opt/endless-grader",
                verifier,
                "python3",
                "-I",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "test_final_state.py",
                "--junitxml=/tmp/endless-results.xml",
            ],
            timeout=120,
            check=False,
        )
        report = env.run_docker(
            ["cp", f"{verifier}:/tmp/endless-results.xml", "-"]
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(report)) as tar:
            member = next(m for m in tar.getmembers() if m.isfile())
            source = tar.extractfile(member)
            assert source is not None
            xml = source.read()
        return (
            completed.returncode,
            completed.stdout.decode(errors="replace"),
            xml,
        )
    finally:
        env.run_docker(["rm", "-f", verifier])
        env.remove_container(verifier)
