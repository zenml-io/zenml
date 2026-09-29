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
"""Run ZenML's opt-in generated test suites with bounded resources."""

import argparse
import importlib.metadata
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FUZZ_ROOT = REPOSITORY_ROOT / "tests" / "fuzz"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / ".fuzz-results"
METADATA_FILENAME = "run.json"

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
HARD_TIMEOUT_SECONDS = {"local": 15 * 60, "pr": 15 * 60, "nightly": 60 * 60}
GENERATION_BUDGET_SECONDS = {
    ("filters", "sqlite", "local"): 60,
    ("filters", "sqlite", "pr"): 180,
    ("filters", "sqlite", "nightly"): 600,
    ("filters", "mysql", "local"): 60,
    ("filters", "mysql", "pr"): 180,
    ("filters", "mysql", "nightly"): 600,
    ("cli", "none", "local"): 60,
    ("cli", "none", "pr"): 120,
    ("cli", "none", "nightly"): 300,
    ("api", "sqlite", "local"): 180,
    ("api", "sqlite", "pr"): 300,
    ("api", "sqlite", "nightly"): 600,
    ("api", "mysql", "local"): 180,
    ("api", "mysql", "pr"): 300,
    ("api", "mysql", "nightly"): 2400,
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
SUPPORT_TEST_PATHS = (
    FUZZ_ROOT / "test_runner.py",
    FUZZ_ROOT / "test_workflow_contract.py",
)
API_SUPPORT_TEST_PATHS = (FUZZ_ROOT / "test_api_harness.py",)
PROCESS_TERMINATION_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class RunConfig:
    """Validated fuzz runner configuration."""

    suite: str
    backend: str
    profile: str
    output_dir: Path
    batches: Optional[int]
    seed: Optional[int]
    reproduce: Optional[str]


@dataclass(frozen=True)
class BatchResult:
    """Result of one bounded pytest process."""

    command: List[str]
    duration_seconds: float
    return_code: int
    status: str
    log_path: Optional[str] = None


def _positive_integer(value: str) -> int:
    """Parse a positive integer for argparse.

    Args:
        value: Raw argument value.

    Returns:
        The parsed positive integer.

    Raises:
        argparse.ArgumentTypeError: If the value is not positive.
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
    """Validate and normalize a pytest node ID for one selected suite."""
    if value is None:
        return None
    expected = SUITE_PATHS[suite]
    relative_path = expected.relative_to(REPOSITORY_ROOT).as_posix()
    accepted_prefixes = (relative_path, expected.name, str(expected))
    for prefix in accepted_prefixes:
        if value == prefix or value.startswith(f"{prefix}::"):
            suffix = value[len(prefix) :]
            return f"{expected}{suffix}"
    parser.error(
        f"--reproduce must select a node from {relative_path} for suite "
        f"'{suite}'"
    )
    return None


def parse_args(arguments: Optional[Sequence[str]] = None) -> RunConfig:
    """Parse and validate command-line arguments without creating resources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, choices=tuple(SUITE_PATHS))
    parser.add_argument(
        "--backend", choices=("sqlite", "mysql", "none"), default=None
    )
    parser.add_argument("--profile", choices=PROFILES, default="local")
    parser.add_argument("--batches", type=_positive_integer)
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
    parsed = parser.parse_args(arguments)
    if parsed.suite == "api" and not _supports_process_group_cleanup():
        parser.error(
            "suite 'api' requires a POSIX host for process-group cleanup"
        )
    backend = parsed.backend or ("none" if parsed.suite == "cli" else "sqlite")
    allowed_backends = SUITE_BACKENDS[parsed.suite]
    if backend not in allowed_backends:
        allowed = " or ".join(f"'{item}'" for item in allowed_backends)
        parser.error(f"suite '{parsed.suite}' requires backend {allowed}")
    if parsed.seed is not None and parsed.batches not in (None, 1):
        parser.error("--seed requires --batches 1 for an exact reproduction")
    if parsed.reproduce is not None and parsed.batches not in (None, 1):
        parser.error("--reproduce requires --batches 1")
    reproduction = _normalize_reproduction(
        parser, parsed.suite, parsed.reproduce
    )
    output_dir = parsed.output_dir or _default_output_dir(
        parsed.suite, backend, parsed.profile
    )
    return RunConfig(
        suite=parsed.suite,
        backend=backend,
        profile=parsed.profile,
        output_dir=output_dir.resolve(),
        batches=parsed.batches,
        seed=parsed.seed,
        reproduce=reproduction,
    )


def _supports_process_group_cleanup() -> bool:
    """Return whether this host supports process-group cleanup."""
    return os.name == "posix"


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
    """Return the tested Git revision, or an explicit unknown value."""
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


def _write_metadata(output_dir: Path, metadata: Mapping[str, object]) -> None:
    """Write current run metadata atomically."""
    destination = output_dir / METADATA_FILENAME
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)


def build_pytest_command(config: RunConfig, batch_number: int) -> List[str]:
    """Build the isolated pytest command for one batch."""
    targets = [config.reproduce or str(SUITE_PATHS[config.suite])]
    exact_run = config.seed is not None or config.reproduce is not None
    if batch_number == 1 and not exact_run:
        targets.extend(str(path) for path in SUPPORT_TEST_PATHS)
        if config.suite == "api":
            targets.extend(str(path) for path in API_SUPPORT_TEST_PATHS)
    command = [
        sys.executable,
        "-m",
        "pytest",
        *targets,
        "--confcutdir",
        str(FUZZ_ROOT),
        "-q",
        f"--hypothesis-profile={config.profile}",
    ]
    for plugin in PYTEST_PLUGIN_BLOCKLIST:
        command.extend(("-p", plugin))
    if config.seed is not None:
        command.append(f"--hypothesis-seed={config.seed}")
    if config.batches is None or config.batches > 1:
        command.append(
            f"--junitxml={config.output_dir / f'batch-{batch_number}.xml'}"
        )
    return command


def _runner_environment(
    config: RunConfig, batch_number: int
) -> Dict[str, str]:
    """Build an isolated, analytics-free environment for pytest."""
    environment = os.environ.copy()
    environment.update(
        {
            "ZENML_FUZZ": "1",
            "ZENML_FUZZ_BACKEND": config.backend,
            "ZENML_FUZZ_BATCH": str(batch_number),
            "ZENML_FUZZ_OUTPUT_DIR": str(config.output_dir),
            "HYPOTHESIS_STORAGE_DIRECTORY": str(
                _hypothesis_storage_directory(config)
            ),
            "ZENML_ANALYTICS_OPT_IN": "false",
            "ZENML_DEBUG": "true",
            "AUTO_OPEN_DASHBOARD": "false",
        }
    )
    return environment


def _hypothesis_storage_directory(config: RunConfig) -> Path:
    """Resolve the reusable Hypothesis corpus directory for a run.

    Args:
        config: Selected fuzz run configuration.

    Returns:
        The external corpus path when configured, otherwise the run-owned path.
    """
    configured = os.environ.get("ZENML_FUZZ_CORPUS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return config.output_dir / "hypothesis"


def terminate_process(process: subprocess.Popen[bytes]) -> bool:
    """Terminate an owned pytest process group, escalating if necessary.

    Returns:
        Whether the process exited within the bounded teardown period.
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
            process.wait(timeout=PROCESS_TERMINATION_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return False
    return True


def run_pytest(
    command: List[str],
    environment: Mapping[str, str],
    timeout_seconds: int,
    output_dir: Path,
) -> BatchResult:
    """Run one pytest batch with a hard timeout and owned teardown."""
    batch_number = environment.get("ZENML_FUZZ_BATCH", "1")
    log_path = output_dir / f"batch-{batch_number}.log"
    started = time.monotonic()
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            env=dict(environment),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            terminated = terminate_process(process)
            return BatchResult(
                command=command,
                duration_seconds=time.monotonic() - started,
                return_code=124 if terminated else 125,
                status="timed_out" if terminated else "teardown_failed",
                log_path=str(log_path),
            )
        except KeyboardInterrupt:
            terminate_process(process)
            raise
    status = (
        "passed"
        if return_code == 0
        else "empty_collection"
        if return_code == 5
        else "failed"
    )
    return BatchResult(
        command=command,
        duration_seconds=time.monotonic() - started,
        return_code=return_code,
        status=status,
        log_path=str(log_path),
    )


def _initial_metadata(config: RunConfig) -> Dict[str, object]:
    """Create metadata shared by setup and test outcomes."""
    return {
        "backend": config.backend,
        "batches": [],
        "generation_budget_seconds": GENERATION_BUDGET_SECONDS[
            (config.suite, config.backend, config.profile)
        ],
        "hard_timeout_seconds": HARD_TIMEOUT_SECONDS[config.profile],
        "hypothesis_storage_directory": str(
            _hypothesis_storage_directory(config)
        ),
        "invocation": build_pytest_command(config, 1),
        "output_dir": str(config.output_dir),
        "profile": config.profile,
        "python_version": sys.version,
        "reproduce": config.reproduce,
        "seed": config.seed,
        "source_path": str(REPOSITORY_ROOT),
        "source_dirty": _source_is_dirty(),
        "source_revision": _source_revision(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "starting",
        "suite": config.suite,
        "tool_versions": _tool_versions(),
    }


def _aggregate_status(batch_results: Sequence[BatchResult]) -> str:
    """Return an overall status without allowing later success to mask failure."""
    statuses = {result.status for result in batch_results}
    for status in (
        "teardown_failed",
        "timed_out",
        "empty_collection",
        "failed",
    ):
        if status in statuses:
            return status
    return "passed"


def _aggregate_return_code(batch_results: Sequence[BatchResult]) -> int:
    """Return the first nonzero batch code, or zero when all passed."""
    return next(
        (result.return_code for result in batch_results if result.return_code),
        0,
    )


def main(arguments: Optional[Sequence[str]] = None) -> int:
    """Run a selected fuzz suite and preserve its reproduction evidence."""
    config = parse_args(arguments)
    try:
        config.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(
            f"Fuzz evidence directory already exists: {config.output_dir}",
            file=sys.stderr,
        )
        return 2

    metadata = _initial_metadata(config)
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
            f"{', '.join(missing)}. Install tests/fuzz/requirements.txt ",
            "beside the editable checkout and retry.",
            sep="",
            file=sys.stderr,
        )
        return 2

    batch_results: List[BatchResult] = []
    started = time.monotonic()
    hard_deadline = started + HARD_TIMEOUT_SECONDS[config.profile]
    generation_deadline = (
        started
        + GENERATION_BUDGET_SECONDS[
            (config.suite, config.backend, config.profile)
        ]
    )
    exact_run = config.seed is not None or config.reproduce is not None
    fixed_batches = 1 if exact_run else config.batches
    batch_number = 1
    try:
        while fixed_batches is None or batch_number <= fixed_batches:
            if (
                fixed_batches is None
                and batch_number > 1
                and time.monotonic() >= generation_deadline
            ):
                break
            command = build_pytest_command(config, batch_number)
            remaining_seconds = math.ceil(hard_deadline - time.monotonic())
            if remaining_seconds <= 0:
                batch_results.append(
                    BatchResult(
                        command=command,
                        duration_seconds=0.0,
                        return_code=124,
                        status="timed_out",
                    )
                )
                metadata["batches"] = [asdict(item) for item in batch_results]
                metadata["status"] = "timed_out"
                _write_metadata(config.output_dir, metadata)
                break
            result = run_pytest(
                command,
                _runner_environment(config, batch_number),
                remaining_seconds,
                config.output_dir,
            )
            batch_results.append(result)
            metadata["batches"] = [asdict(item) for item in batch_results]
            metadata["status"] = _aggregate_status(batch_results)
            _write_metadata(config.output_dir, metadata)
            if result.status in {
                "teardown_failed",
                "timed_out",
                "empty_collection",
            }:
                break
            batch_number += 1
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
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": _aggregate_status(batch_results),
        }
    )
    _write_metadata(config.output_dir, metadata)
    return _aggregate_return_code(batch_results)


if __name__ == "__main__":
    sys.exit(main())
