#!/usr/bin/env python3
"""Utilities for running ZenML unit-test shards on Modal sandboxes.

This script is intentionally CI-focused. GitHub Actions remains the source of
truth for orchestration, logs, pass/fail status, and artifact handling while
Modal is used only as the remote execution substrate.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import posixpath
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TextIO

import modal

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP_NAME = "zenml-ci-unit-tests"
DEFAULT_TIMEOUT_SECONDS = 7200
GIT_ARCHIVE_REMOTE_PATH = "/tmp/zenml-source.tar.gz"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_image(
    *,
    python_version: str,
    requirements_path: Path,
    apt_packages: list[str],
) -> modal.Image:
    image = modal.Image.debian_slim(python_version=python_version)
    if apt_packages:
        image = image.apt_install(*apt_packages)

    image = image.add_local_file(
        str(requirements_path),
        remote_path="/tmp/zenml-modal-requirements.txt",
        copy=True,
    ).run_commands(
        "python -m pip install --upgrade wheel pip uv",
        "uv pip install --system -r /tmp/zenml-modal-requirements.txt",
        "uv pip uninstall --system multipart || true",
    )

    return image


@contextmanager
def _force_rebuild(enabled: bool) -> Iterable[None]:
    if not enabled:
        yield
        return

    old_force_build = os.environ.get("MODAL_FORCE_BUILD")
    old_ignore_cache = os.environ.get("MODAL_IGNORE_CACHE")
    os.environ["MODAL_FORCE_BUILD"] = "1"
    os.environ["MODAL_IGNORE_CACHE"] = "1"
    try:
        yield
    finally:
        if old_force_build is None:
            os.environ.pop("MODAL_FORCE_BUILD", None)
        else:
            os.environ["MODAL_FORCE_BUILD"] = old_force_build

        if old_ignore_cache is None:
            os.environ.pop("MODAL_IGNORE_CACHE", None)
        else:
            os.environ["MODAL_IGNORE_CACHE"] = old_ignore_cache


def prepare_image(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="zenml-modal-image-spec-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        requirements_path = temp_dir / "requirements.txt"
        apt_packages_path = temp_dir / "apt-packages.txt"

        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "export_ci_image_spec.py"),
                "--python-version",
                args.python_version,
                "--target-os",
                "Linux",
                "--install-integrations",
                args.install_integrations,
                "--output-requirements",
                str(requirements_path),
                "--output-apt-packages",
                str(apt_packages_path),
            ],
            check=True,
            cwd=REPO_ROOT,
        )

        apt_packages = [
            line.strip()
            for line in apt_packages_path.read_text().splitlines()
            if line.strip()
        ]

        image_id: str | None = None
        with _force_rebuild(args.force_rebuild):
            with modal.enable_output():
                image = _build_image(
                    python_version=args.python_version,
                    requirements_path=requirements_path,
                    apt_packages=apt_packages,
                )
                app = modal.App.lookup(args.app_name, create_if_missing=True)
                LOGGER.info(
                    "Preparing Modal image for Python %s (integrations=%s)...",
                    args.python_version,
                    args.install_integrations,
                )
                image.build(app)
                # Force materialization so `object_id` is guaranteed to exist.
                sandbox = modal.Sandbox.create(app=app, image=image, timeout=30)
                sandbox.terminate()
                image_id = image.object_id

    if not image_id:
        raise RuntimeError("Modal image did not return an image ID.")

    print(image_id)
    return 0


def _stream_reader(
    *,
    reader: Iterable[str | bytes],
    destination: TextIO,
    log_path: Path,
    mode: str = "a",
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open(mode, encoding="utf-8") as log_file:
        for chunk in reader:
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="replace")
            print(chunk, end="", file=destination, flush=True)
            log_file.write(chunk)
            log_file.flush()


def _download_file(
    *,
    sandbox: modal.Sandbox,
    remote_path: str,
    local_path: Path,
    required: bool,
) -> bool:
    try:
        with sandbox.open(remote_path, "rb") as remote_file:
            data = remote_file.read()
    except Exception as exc:  # noqa: BLE001
        if required:
            raise RuntimeError(
                f"Failed to download required artifact '{remote_path}': {exc}"
            ) from exc

        LOGGER.warning(
            "Optional artifact %s was not available for download: %s",
            remote_path,
            exc,
        )
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return True


def _join_stream_thread(thread: threading.Thread, *, name: str) -> None:
    thread.join(timeout=30)
    if thread.is_alive():
        raise RuntimeError(
            f"Timed out while waiting for Modal {name} log stream to finish."
        )


def _stream_process_output(
    *,
    process: object,
    stdout_path: Path,
    stderr_path: Path,
    truncate_logs: bool = False,
) -> int:
    stdout_mode = "w" if truncate_logs else "a"
    stderr_mode = "w" if truncate_logs else "a"
    stdout_thread = threading.Thread(
        target=_stream_reader,
        kwargs={
            "reader": process.stdout,
            "destination": sys.stdout,
            "log_path": stdout_path,
            "mode": stdout_mode,
        },
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_reader,
        kwargs={
            "reader": process.stderr,
            "destination": sys.stderr,
            "log_path": stderr_path,
            "mode": stderr_mode,
        },
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    process.wait()
    _join_stream_thread(stdout_thread, name="stdout")
    _join_stream_thread(stderr_thread, name="stderr")
    return int(process.returncode)


def _resolve_source_ref(explicit_ref: str | None = None) -> str:
    if explicit_ref:
        return explicit_ref

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _create_git_archive(*, ref: str, archive_path: Path) -> None:
    subprocess.run(
        ["git", "archive", "--format=tar.gz", "-o", str(archive_path), ref],
        check=True,
        cwd=REPO_ROOT,
    )


def _upload_file_to_sandbox(
    *,
    sandbox: modal.Sandbox,
    local_path: Path,
    remote_path: str,
) -> None:
    remote_parent = posixpath.dirname(remote_path)
    if remote_parent:
        sandbox.mkdir(remote_parent, parents=True)

    with local_path.open("rb") as local_file, sandbox.open(remote_path, "wb") as remote_file:
        shutil.copyfileobj(local_file, remote_file, length=4 * 1024 * 1024)


def _run_sandbox_command(
    *,
    sandbox: modal.Sandbox,
    command: str,
    description: str,
    stdout_path: Path,
    stderr_path: Path,
    truncate_logs: bool = False,
) -> None:
    LOGGER.info("%s...", description)
    process = sandbox.exec("bash", "-lc", command)
    return_code = _stream_process_output(
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        truncate_logs=truncate_logs,
    )
    if return_code != 0:
        raise RuntimeError(
            f"{description} failed with exit code {return_code}."
        )



def _write_metadata(
    *,
    metadata_path: Path,
    payload: dict[str, object],
) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _make_remote_test_command(args: argparse.Namespace) -> str:
    artifact_dir = "/tmp/zenml-modal-artifacts"
    pytest_target = shlex.quote(args.pytest_target)
    test_environment = shlex.quote(args.test_environment)
    return f"""
set -euo pipefail
cd /workspace
mkdir -p {artifact_dir}
export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export PYTHONIOENCODING=utf-8
export UV_HTTP_TIMEOUT=600
export PYTEST_RERUNS={int(args.reruns)}
export EVIDENTLY_DISABLE_TELEMETRY=1
set +e
coverage run -m pytest {pytest_target} \\
  --color=yes \\
  -vv \\
  --environment {test_environment} \\
  --no-provision \\
  --durations-path=.test_durations \\
  --splits={int(args.shard_count)} \\
  --group={int(args.shard_index)} \\
  --splitting-algorithm least_duration \\
  --reruns {int(args.reruns)} \\
  --reruns-delay 5 \\
  --instafail \\
  --junitxml={artifact_dir}/junit.xml
exit_code=$?
if [ -f .coverage ]; then
  mv .coverage {artifact_dir}/.coverage.{int(args.shard_index)}
fi
exit "$exit_code"
""".strip()


def run_unit_shard(args: argparse.Namespace) -> int:
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = artifact_dir / "stdout.log"
    stderr_path = artifact_dir / "stderr.log"
    metadata_path = artifact_dir / "metadata.json"
    source_ref = _resolve_source_ref(args.source_ref)

    metadata: dict[str, object] = {
        "app_name": args.app_name,
        "image_id": args.image_id,
        "shard_count": int(args.shard_count),
        "shard_index": int(args.shard_index),
        "cpu": float(args.cpu),
        "memory_mb": int(args.memory_mb),
        "source_ref": source_ref,
        "started_at": _utc_now(),
    }
    _write_metadata(metadata_path=metadata_path, payload=metadata)

    app = modal.App.lookup(args.app_name, create_if_missing=True)
    image = modal.Image.from_id(args.image_id)

    sandbox: modal.Sandbox | None = None
    process = None
    cleanup_error: Exception | None = None

    try:
        LOGGER.info(
            "Creating Modal sandbox for shard %s/%s (cpu=%s, memory_mb=%s)...",
            args.shard_index,
            args.shard_count,
            args.cpu,
            args.memory_mb,
        )
        sandbox = modal.Sandbox.create(
            app=app,
            image=image,
            cpu=float(args.cpu),
            memory=int(args.memory_mb),
            timeout=int(args.timeout_seconds),
            workdir="/workspace",
        )
        metadata["sandbox_id"] = sandbox.object_id
        _write_metadata(metadata_path=metadata_path, payload=metadata)

        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")

        with tempfile.NamedTemporaryFile(
            prefix="zenml-modal-source-", suffix=".tar.gz", delete=False
        ) as archive_file:
            archive_path = Path(archive_file.name)
        try:
            LOGGER.info("Creating git archive for source ref %s...", source_ref)
            _create_git_archive(ref=source_ref, archive_path=archive_path)
            LOGGER.info("Uploading git archive for source ref %s...", source_ref)
            _upload_file_to_sandbox(
                sandbox=sandbox,
                local_path=archive_path,
                remote_path=GIT_ARCHIVE_REMOTE_PATH,
            )
        finally:
            archive_path.unlink(missing_ok=True)

        _run_sandbox_command(
            sandbox=sandbox,
            description="Extracting git snapshot into sandbox workspace",
            command=(
                "mkdir -p /workspace && "
                f"tar -xzf {shlex.quote(GIT_ARCHIVE_REMOTE_PATH)} -C /workspace && "
                f"rm -f {shlex.quote(GIT_ARCHIVE_REMOTE_PATH)}"
            ),
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            truncate_logs=True,
        )
        _run_sandbox_command(
            sandbox=sandbox,
            description="Installing ZenML source in sandbox",
            command=(
                'cd /workspace && '
                'uv pip install --system "setuptools<82" && '
                'uv pip install --system -e . --no-deps'
            ),
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

        command = _make_remote_test_command(args)
        LOGGER.info("Starting remote pytest shard...")
        process = sandbox.exec("bash", "-lc", command)
        exit_code = _stream_process_output(
            process=process,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        metadata["exit_code"] = exit_code

        remote_artifact_root = "/tmp/zenml-modal-artifacts"
        coverage_downloaded = _download_file(
            sandbox=sandbox,
            remote_path=f"{remote_artifact_root}/.coverage.{int(args.shard_index)}",
            local_path=artifact_dir / f".coverage.{int(args.shard_index)}",
            required=False,
        )
        junit_downloaded = _download_file(
            sandbox=sandbox,
            remote_path=f"{remote_artifact_root}/junit.xml",
            local_path=artifact_dir / "junit.xml",
            required=False,
        )
        metadata["coverage_downloaded"] = coverage_downloaded
        metadata["junit_downloaded"] = junit_downloaded

        if exit_code == 0 and not coverage_downloaded:
            raise RuntimeError(
                f"Shard {args.shard_index} passed but no coverage artifact was downloaded."
            )
        if exit_code == 0 and not junit_downloaded:
            raise RuntimeError(
                f"Shard {args.shard_index} passed but no JUnit artifact was downloaded."
            )
        if not coverage_downloaded and not junit_downloaded:
            LOGGER.warning(
                "Shard %s finished without downloadable coverage or JUnit artifacts.",
                args.shard_index,
            )
    finally:
        if sandbox is not None:
            try:
                sandbox.terminate()
                metadata["cleanup_status"] = "terminated"
            except Exception as exc:  # noqa: BLE001
                cleanup_error = exc
                metadata["cleanup_status"] = "failed"
                metadata["cleanup_error"] = str(exc)
        metadata["finished_at"] = _utc_now()
        _write_metadata(metadata_path=metadata_path, payload=metadata)

    if cleanup_error is not None:
        exit_code = int(metadata.get("exit_code", 1))
        if exit_code == 0:
            raise RuntimeError(
                f"Modal sandbox cleanup failed for shard {args.shard_index}: {cleanup_error}"
            ) from cleanup_error

        LOGGER.warning(
            "Shard %s already failed with exit code %s and sandbox cleanup also failed: %s",
            args.shard_index,
            exit_code,
            cleanup_error,
        )

    return int(metadata.get("exit_code", 1))


def combine_coverage(args: argparse.Namespace) -> int:
    artifact_root = Path(args.artifact_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    coverage_files = sorted(artifact_root.rglob(".coverage.*"))
    if not coverage_files:
        LOGGER.error(
            "No shard coverage files found under artifact root %s. "
            "All shards may have failed before coverage data was written.",
            artifact_root,
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="modal-coverage-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for coverage_file in coverage_files:
            shutil.copy2(coverage_file, temp_dir / coverage_file.name)

        env = os.environ.copy()
        env["COVERAGE_FILE"] = str(output_dir / ".coverage")

        subprocess.run(
            [sys.executable, "-m", "coverage", "combine", str(temp_dir)],
            check=True,
            cwd=REPO_ROOT,
            env=env,
        )
        subprocess.run(
            [sys.executable, "-m", "coverage", "report", "--show-missing"],
            check=True,
            cwd=REPO_ROOT,
            env=env,
        )
        subprocess.run(
            [sys.executable, "-m", "coverage", "xml", "-o", str(output_dir / "coverage.xml")],
            check=True,
            cwd=REPO_ROOT,
            env=env,
        )

    summary = {
        "coverage_files_combined": len(coverage_files),
        "generated_at": _utc_now(),
    }
    (output_dir / "coverage-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare-image", help="Build or reuse the Modal image for unit tests."
    )
    prepare_parser.add_argument("--python-version", default="3.11")
    prepare_parser.add_argument(
        "--install-integrations",
        choices=("yes", "no"),
        default="yes",
    )
    prepare_parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    prepare_parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force Modal to ignore the image cache for this build.",
    )
    prepare_parser.set_defaults(func=prepare_image)

    shard_parser = subparsers.add_parser(
        "run-unit-shard",
        help="Run one unit-test shard in a Modal sandbox with live log streaming.",
    )
    shard_parser.add_argument("--image-id", required=True)
    shard_parser.add_argument("--shard-count", type=int, required=True)
    shard_parser.add_argument("--shard-index", type=int, required=True)
    shard_parser.add_argument("--artifact-dir", required=True)
    shard_parser.add_argument("--pytest-target", default="tests/unit")
    shard_parser.add_argument("--test-environment", default="default")
    shard_parser.add_argument("--reruns", type=int, default=3)
    shard_parser.add_argument("--cpu", type=float, default=4.0)
    shard_parser.add_argument("--memory-mb", type=int, default=16384)
    shard_parser.add_argument(
        "--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS
    )
    shard_parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    shard_parser.add_argument(
        "--source-ref",
        default=None,
        help="Git ref to archive into the sandbox. Defaults to the checked-out HEAD.",
    )
    shard_parser.set_defaults(func=run_unit_shard)

    combine_parser = subparsers.add_parser(
        "combine-coverage", help="Combine shard coverage files into one report."
    )
    combine_parser.add_argument("--artifact-root", required=True)
    combine_parser.add_argument("--output-dir", required=True)
    combine_parser.set_defaults(func=combine_coverage)

    return parser


def main() -> int:
    _configure_logging()
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
