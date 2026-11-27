#!/usr/bin/env python3
#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Run ZenML's opt-in generated fuzz suites with bounded timeouts."""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FUZZ_ROOT = REPOSITORY_ROOT / "tests" / "fuzz"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / ".fuzz-results"
METADATA_FILENAME = "run.json"
LOG_FILENAME = "fuzz.log"

SUITE_PATHS = {
    "filters": FUZZ_ROOT / "test_filters.py",
    "cli": FUZZ_ROOT / "test_cli.py",
    "api": FUZZ_ROOT / "test_api.py",
}
SUITE_BACKENDS = {
    "filters": ("sqlite", "mysql"),
    "cli": ("none",),
    "api": ("sqlite", "mysql"),
}
SUITE_DEPENDENCIES = {
    "filters": ("pytest", "hypothesis"),
    "cli": ("pytest", "hypothesis"),
    "api": ("pytest", "hypothesis", "schemathesis"),
}
PROFILES = ("local", "pr", "nightly")
HARD_TIMEOUT_SECONDS = {
    "local": 15 * 60,
    "pr": 15 * 60,
    "nightly": 55 * 60,
}
PYTEST_PLUGIN_BLOCKLIST = (
    "no:rerunfailures",
    "no:randomly",
    "no:pytest_randomly",
    "no:ordering",
    "no:pytest_order",
    "no:xdist",
)
TOOL_DISTRIBUTIONS = ("zenml", "pytest", "hypothesis", "schemathesis")
# Allow enough time after SIGTERM for pytest to unwind fixtures, stop Uvicorn
# (10s limit), and drop disposable MySQL databases before escalating to SIGKILL.
PROCESS_TERMINATION_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class RunConfig:
    """Validated fuzz runner configuration."""

    suite: str
    backend: str
    profile: str
    output_dir: Path
    seed: Optional[int]
    reproduce: Optional[str]
    timeout_seconds: int


@dataclass(frozen=True)
class RunResult:
    """Result of the bounded pytest execution."""

    command: List[str]
    duration_seconds: float
    return_code: int
    status: str
    log_path: str


def _positive_integer(value: str) -> int:
    """Parse a positive integer for argparse.

    Args:
        value: Raw CLI value.

    Returns:
        Parsed positive integer.

    Raises:
        argparse.ArgumentTypeError: If the value is not a positive integer.
    """
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "must be a positive integer"
        ) from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _default_output_dir(suite: str, backend: str, profile: str) -> Path:
    """Return a unique default evidence directory."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return DEFAULT_OUTPUT_ROOT / (
        f"{timestamp}-{suite}-{backend}-{profile}-{os.getpid()}"
    )


def _normalize_reproduction(
    parser: argparse.ArgumentParser, suite: str, value: Optional[str]
) -> Optional[str]:
    """Validate and normalize a pytest node ID for the selected suite."""
    if value is None:
        return None
    expected = SUITE_PATHS[suite]
    relative_path = expected.relative_to(REPOSITORY_ROOT).as_posix()
    for prefix in (relative_path, expected.name, str(expected)):
        if value == prefix or value.startswith(f"{prefix}::"):
            return f"{expected}{value[len(prefix) :]}"
    parser.error(
        f"--reproduce must select a node from {relative_path} for suite "
        f"'{suite}'"
    )
    return None


def parse_args(arguments: Optional[Sequence[str]] = None) -> RunConfig:
    """Parse and validate CLI arguments without creating directories.

    Args:
        arguments: Optional explicit argument sequence.

    Returns:
        Validated runner configuration.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, choices=tuple(SUITE_PATHS))
    parser.add_argument(
        "--backend", choices=("sqlite", "mysql", "none"), default=None
    )
    parser.add_argument("--profile", choices=PROFILES, default="local")
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--reproduce",
        help="Pytest node ID within the selected suite to reproduce.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New directory in which to preserve run evidence.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_integer,
        default=None,
        help="Override the profile's hard wall-clock timeout in seconds.",
    )
    parsed = parser.parse_args(arguments)
    if parsed.suite == "api" and os.name != "posix":
        parser.error(
            "suite 'api' requires a POSIX host for process-group cleanup"
        )
    backend = parsed.backend or ("none" if parsed.suite == "cli" else "sqlite")
    allowed_backends = SUITE_BACKENDS[parsed.suite]
    if backend not in allowed_backends:
        allowed = " or ".join(f"'{item}'" for item in allowed_backends)
        parser.error(f"suite '{parsed.suite}' requires backend {allowed}")
    reproduction = _normalize_reproduction(
        parser, parsed.suite, parsed.reproduce
    )
    output_dir = parsed.output_dir or _default_output_dir(
        parsed.suite, backend, parsed.profile
    )
    timeout_seconds = (
        parsed.timeout_seconds
        if parsed.timeout_seconds is not None
        else HARD_TIMEOUT_SECONDS[parsed.profile]
    )
    return RunConfig(
        suite=parsed.suite,
        backend=backend,
        profile=parsed.profile,
        output_dir=output_dir.resolve(),
        seed=parsed.seed,
        reproduce=reproduction,
        timeout_seconds=timeout_seconds,
    )


def missing_dependencies(suite: str) -> List[str]:
    """Return missing optional modules required by a suite."""
    return [
        module
        for module in SUITE_DEPENDENCIES[suite]
        if importlib.util.find_spec(module) is None
    ]


def _tool_versions() -> Dict[str, Optional[str]]:
    """Return installed versions for tools needed to reproduce a run."""
    versions: Dict[str, Optional[str]] = {}
    for distribution in TOOL_DISTRIBUTIONS:
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def _source_revision() -> str:
    """Return the tested Git revision, or ``unknown`` if unavailable."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _source_is_dirty() -> Optional[bool]:
    """Return whether tracked or untracked source changes are present."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout) if result.returncode == 0 else None


def _hypothesis_storage_directory(config: RunConfig) -> Path:
    """Resolve the reusable Hypothesis corpus directory for a run."""
    configured = os.environ.get("ZENML_FUZZ_CORPUS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return config.output_dir / "hypothesis"


def build_pytest_command(config: RunConfig) -> List[str]:
    """Build the isolated pytest command for the selected suite.

    Args:
        config: Validated runner configuration.

    Returns:
        Full pytest argument list.
    """
    target = config.reproduce or str(SUITE_PATHS[config.suite])
    command = [
        sys.executable,
        "-m",
        "pytest",
        target,
        "--confcutdir",
        str(FUZZ_ROOT),
        "-v",
        "--durations=20",
        "--hypothesis-show-statistics",
        f"--hypothesis-profile={config.profile}",
        f"--junitxml={config.output_dir / 'junit.xml'}",
    ]
    for plugin in PYTEST_PLUGIN_BLOCKLIST:
        command.extend(("-p", plugin))
    if config.seed is not None:
        command.append(f"--hypothesis-seed={config.seed}")
    return command


def _runner_environment(config: RunConfig) -> Dict[str, str]:
    """Build an isolated, unbuffered environment for the fuzz process."""
    environment = os.environ.copy()
    environment.update(
        {
            "AUTO_OPEN_DASHBOARD": "false",
            "HYPOTHESIS_STORAGE_DIRECTORY": str(
                _hypothesis_storage_directory(config)
            ),
            "PYTHONUNBUFFERED": "1",
            "ZENML_ANALYTICS_OPT_IN": "false",
            "ZENML_DEBUG": "true",
            "ZENML_FUZZ": "1",
            "ZENML_FUZZ_BACKEND": config.backend,
            "ZENML_FUZZ_OUTPUT_DIR": str(config.output_dir),
        }
    )
    return environment


def _write_metadata(output_dir: Path, metadata: Mapping[str, object]) -> None:
    """Write run metadata atomically."""
    destination = output_dir / METADATA_FILENAME
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)


def terminate_process(process: subprocess.Popen[bytes]) -> bool:
    """Terminate an owned pytest process group, escalating to SIGKILL if stuck.

    Args:
        process: Owned subprocess to terminate.

    Returns:
        Whether the process exited within the bounded grace period.
    """
    if process.poll() is not None:
        return True
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return True
    try:
        process.wait(timeout=PROCESS_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            return True
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            return False
    return True


def _stream_output(
    pipe: object, log_file: object, stdout_stream: object
) -> None:
    """Copy child output bytes to both the log file and console live."""
    while True:
        chunk = pipe.read(4096)  # type: ignore[attr-defined]
        if not chunk:
            break
        log_file.write(chunk)  # type: ignore[attr-defined]
        log_file.flush()  # type: ignore[attr-defined]
        stdout_stream.write(chunk)  # type: ignore[attr-defined]
        stdout_stream.flush()  # type: ignore[attr-defined]


def run_pytest(
    command: List[str],
    environment: Mapping[str, str],
    timeout_seconds: int,
    output_dir: Path,
) -> RunResult:
    """Run pytest with live output streaming, hard timeout, and clean teardown.

    Args:
        command: Pytest command arguments.
        environment: Environment variables for the child process.
        timeout_seconds: Maximum wall-clock runtime before SIGTERM.
        output_dir: Run-owned evidence directory.

    Returns:
        Recorded outcome of the pytest execution.
    """
    log_path = output_dir / LOG_FILENAME
    started = time.monotonic()
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            env=dict(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
        assert process.stdout is not None
        reader = threading.Thread(
            target=_stream_output,
            args=(process.stdout, log_file, sys.stdout.buffer),
            daemon=True,
        )
        reader.start()
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            terminated = terminate_process(process)
            reader.join(timeout=5)
            return RunResult(
                command=command,
                duration_seconds=round(time.monotonic() - started, 3),
                return_code=124 if terminated else 125,
                status="timed_out" if terminated else "teardown_failed",
                log_path=str(log_path),
            )
        except KeyboardInterrupt:
            terminate_process(process)
            reader.join(timeout=5)
            raise
        reader.join(timeout=5)

    status = (
        "passed"
        if return_code == 0
        else "empty_collection"
        if return_code == 5
        else "failed"
    )
    return RunResult(
        command=command,
        duration_seconds=round(time.monotonic() - started, 3),
        return_code=return_code,
        status=status,
        log_path=str(log_path),
    )


def main(arguments: Optional[Sequence[str]] = None) -> int:
    """Run one selected fuzz suite and preserve its reproduction evidence.

    Args:
        arguments: Optional CLI arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Exit code suitable for ``sys.exit``.
    """
    config = parse_args(arguments)
    # Check Git cleanliness before creating output_dir so an unignored output
    # path cannot make clean CI checkouts report ``source_dirty: true``.
    source_dirty = _source_is_dirty()
    source_revision = _source_revision()
    try:
        config.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(
            f"Fuzz evidence directory already exists: {config.output_dir}",
            file=sys.stderr,
        )
        return 2

    command = build_pytest_command(config)
    metadata: Dict[str, object] = {
        "backend": config.backend,
        "hard_timeout_seconds": config.timeout_seconds,
        "hypothesis_storage_directory": str(
            _hypothesis_storage_directory(config)
        ),
        "invocation": command,
        "output_dir": str(config.output_dir),
        "profile": config.profile,
        "python_version": sys.version,
        "reproduce": config.reproduce,
        "seed": config.seed,
        "source_dirty": source_dirty,
        "source_path": str(REPOSITORY_ROOT),
        "source_revision": source_revision,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "starting",
        "suite": config.suite,
        "tool_versions": _tool_versions(),
    }
    _write_metadata(config.output_dir, metadata)

    missing = missing_dependencies(config.suite)
    if missing:
        metadata.update(
            {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "missing_dependencies": missing,
                "status": "setup_failed",
            }
        )
        _write_metadata(config.output_dir, metadata)
        print(
            "Missing fuzz dependencies: "
            f"{', '.join(missing)}. Install tests/fuzz/requirements.txt "
            "beside the editable checkout and retry.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_pytest(
            command,
            _runner_environment(config),
            config.timeout_seconds,
            config.output_dir,
        )
    except KeyboardInterrupt:
        metadata.update(
            {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "interrupted",
            }
        )
        _write_metadata(config.output_dir, metadata)
        return 130
    except OSError as error:
        metadata.update(
            {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "setup_error": str(error),
                "status": "setup_failed",
            }
        )
        _write_metadata(config.output_dir, metadata)
        print(f"Unable to start fuzz test process: {error}", file=sys.stderr)
        return 2

    metadata.update(
        {
            "duration_seconds": result.duration_seconds,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "log_path": result.log_path,
            "return_code": result.return_code,
            "status": result.status,
        }
    )
    _write_metadata(config.output_dir, metadata)
    return result.return_code


if __name__ == "__main__":
    sys.exit(main())
