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
"""Tests for the opt-in fuzz test runner."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from scripts import fuzz


def _result(return_code: int, status: str = "passed") -> fuzz.BatchResult:
    """Create a batch result for runner tests."""
    return fuzz.BatchResult(
        command=["python", "-m", "pytest"],
        duration_seconds=0.01,
        return_code=return_code,
        status=status,
    )


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--suite", "unknown"], "invalid choice"),
        (
            ["--suite", "cli", "--backend", "sqlite"],
            "requires backend 'none'",
        ),
        (
            ["--suite", "filters", "--backend", "none"],
            "requires backend 'sqlite' or 'mysql'",
        ),
        (
            ["--suite", "filters", "--batches", "0"],
            "positive integer",
        ),
    ],
)
def test_invalid_selection_fails_before_output_creation(
    arguments: List[str],
    message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid selections fail without creating an evidence directory."""
    output_path = tmp_path / "evidence"

    with pytest.raises(SystemExit):
        fuzz.parse_args([*arguments, "--output-dir", str(output_path)])

    assert message in capsys.readouterr().err
    assert not output_path.exists()


def test_api_suite_rejects_hosts_without_process_group_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """API fuzzing fails closed when timeout cleanup cannot be guaranteed."""
    monkeypatch.setattr(
        "scripts.fuzz._supports_process_group_cleanup", lambda: False
    )

    with pytest.raises(SystemExit):
        fuzz.parse_args(
            [
                "--suite",
                "api",
                "--output-dir",
                str(tmp_path / "api"),
            ]
        )

    assert "requires a POSIX host" in capsys.readouterr().err


def test_pytest_command_is_isolated_and_selects_one_suite(
    tmp_path: Path,
) -> None:
    """The generated command cuts off parent fixtures and disables retries."""
    config = fuzz.RunConfig(
        suite="filters",
        backend="sqlite",
        profile="pr",
        output_dir=tmp_path,
        batches=1,
        seed=123,
        reproduce=None,
    )

    command = fuzz.build_pytest_command(config, batch_number=1)

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert str(fuzz.FUZZ_ROOT / "test_filters.py") in command
    assert ["--confcutdir", str(fuzz.FUZZ_ROOT)] == command[
        command.index("--confcutdir") : command.index("--confcutdir") + 2
    ]
    assert "--hypothesis-profile=pr" in command
    assert "--hypothesis-seed=123" in command
    assert "-p" in command
    assert "no:rerunfailures" in command
    assert "no:randomly" in command
    assert "test_cli.py" not in " ".join(command)


@pytest.mark.parametrize(
    ("suite", "expected_support_test"),
    [
        ("filters", None),
        ("cli", None),
        ("api", "test_api_harness.py"),
    ],
)
def test_first_batch_runs_support_tests(
    suite: str, expected_support_test: Optional[str], tmp_path: Path
) -> None:
    """Normal first batches exercise runner and workflow support contracts."""
    config = fuzz.RunConfig(
        suite=suite,
        backend="none" if suite == "cli" else "sqlite",
        profile="local",
        output_dir=tmp_path,
        batches=None,
        seed=None,
        reproduce=None,
    )

    first_command = fuzz.build_pytest_command(config, batch_number=1)
    later_command = fuzz.build_pytest_command(config, batch_number=2)

    assert str(fuzz.FUZZ_ROOT / "test_runner.py") in first_command
    assert str(fuzz.FUZZ_ROOT / "test_workflow_contract.py") in first_command
    if expected_support_test:
        assert str(fuzz.FUZZ_ROOT / expected_support_test) in first_command
    else:
        assert str(fuzz.FUZZ_ROOT / "test_api_harness.py") not in first_command
    assert later_command.count(str(fuzz.SUITE_PATHS[suite])) == 1
    assert not any(
        str(path) in later_command
        for path in (*fuzz.SUPPORT_TEST_PATHS, *fuzz.API_SUPPORT_TEST_PATHS)
    )


@pytest.mark.parametrize("exact_option", ["seed", "reproduce"])
def test_exact_runs_only_select_the_generated_suite(
    exact_option: str, tmp_path: Path
) -> None:
    """Seeded and node-specific reproduction runs stay single-targeted."""
    config = fuzz.RunConfig(
        suite="filters",
        backend="sqlite",
        profile="local",
        output_dir=tmp_path,
        batches=None,
        seed=42 if exact_option == "seed" else None,
        reproduce=(
            str(fuzz.SUITE_PATHS["filters"]) + "::test_example"
            if exact_option == "reproduce"
            else None
        ),
    )

    command = fuzz.build_pytest_command(config, batch_number=1)

    assert not any(
        str(path) in command
        for path in (*fuzz.SUPPORT_TEST_PATHS, *fuzz.API_SUPPORT_TEST_PATHS)
    )


@pytest.mark.parametrize(
    "exact_arguments",
    [
        ["--seed", "42"],
        [
            "--reproduce",
            "tests/fuzz/test_filters.py::test_example",
        ],
    ],
)
def test_exact_runs_execute_one_batch(
    exact_arguments: List[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exact runs execute once even without an explicit batch count."""
    commands = []
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])

    def run_batch(
        command: List[str],
        environment: object,
        timeout_seconds: int,
        output_dir: Path,
    ) -> fuzz.BatchResult:
        commands.append(command)
        return _result(0)

    monkeypatch.setattr(fuzz, "run_pytest", run_batch)

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            *exact_arguments,
            "--output-dir",
            str(tmp_path / exact_arguments[0].removeprefix("--")),
        ]
    )

    assert return_code == 0
    assert len(commands) == 1


def test_runner_can_reuse_an_external_hypothesis_corpus(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nightly runs can restore a corpus outside the new evidence directory."""
    corpus_path = tmp_path / "restored-corpus"
    output_path = tmp_path / "new-evidence"
    observed_environment: Dict[str, str] = {}
    monkeypatch.setenv("ZENML_FUZZ_CORPUS_DIR", str(corpus_path))
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])

    def run_batch(
        command: List[str],
        environment: object,
        timeout_seconds: int,
        output_dir: Path,
    ) -> fuzz.BatchResult:
        assert isinstance(environment, dict)
        observed_environment.update(environment)
        return _result(0)

    monkeypatch.setattr(fuzz, "run_pytest", run_batch)

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--profile",
            "nightly",
            "--batches",
            "1",
            "--output-dir",
            str(output_path),
        ]
    )
    metadata = json.loads((output_path / "run.json").read_text())

    assert return_code == 0
    assert observed_environment["HYPOTHESIS_STORAGE_DIRECTORY"] == str(
        corpus_path
    )
    assert metadata["hypothesis_storage_directory"] == str(corpus_path)


def test_reproduction_must_belong_to_selected_suite(tmp_path: Path) -> None:
    """A reproduction selector cannot escape the selected suite."""
    output_path = tmp_path / "evidence"

    with pytest.raises(SystemExit):
        fuzz.parse_args(
            [
                "--suite",
                "filters",
                "--reproduce",
                "tests/fuzz/test_cli.py::test_something",
                "--output-dir",
                str(output_path),
            ]
        )

    assert not output_path.exists()


def test_missing_dependency_is_actionable_and_recorded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An explicitly requested suite records missing optional tools."""
    output_path = tmp_path / "evidence"
    monkeypatch.setattr(
        fuzz, "missing_dependencies", lambda suite: ["hypothesis"]
    )

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--batches",
            "1",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code != 0
    assert metadata["status"] == "setup_failed"
    assert metadata["missing_dependencies"] == ["hypothesis"]
    assert "tests/fuzz/requirements.txt" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("batch_result", "expected_status"),
    [
        (_result(5, "empty_collection"), "empty_collection"),
        (_result(1, "failed"), "failed"),
        (_result(124, "timed_out"), "timed_out"),
        (_result(125, "teardown_failed"), "teardown_failed"),
    ],
)
def test_nonzero_batch_outcomes_are_recorded(
    batch_result: fuzz.BatchResult,
    expected_status: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Empty collection, failure, and timeout remain nonzero outcomes."""
    output_path = tmp_path / expected_status
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])
    monkeypatch.setattr(
        fuzz, "run_pytest", lambda *args, **kwargs: batch_result
    )

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--batches",
            "1",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code != 0
    assert metadata["status"] == expected_status
    assert metadata["batches"][0]["return_code"] == batch_result.return_code


def test_successful_batch_records_reproduction_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A bounded successful run records its source and configuration."""
    output_path = tmp_path / "passed"
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])
    monkeypatch.setattr(fuzz, "run_pytest", lambda *args, **kwargs: _result(0))

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--backend",
            "sqlite",
            "--profile",
            "local",
            "--seed",
            "42",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code == 0
    assert metadata["status"] == "passed"
    assert metadata["suite"] == "filters"
    assert metadata["backend"] == "sqlite"
    assert metadata["profile"] == "local"
    assert metadata["seed"] == 42
    assert metadata["source_path"] == str(fuzz.REPOSITORY_ROOT)
    assert metadata["source_revision"]
    assert metadata["source_dirty"] is not None
    assert metadata["invocation"]
    assert metadata["python_version"]
    assert metadata["tool_versions"]


def test_failure_is_not_masked_by_a_later_passing_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A later success cannot convert an earlier fuzz failure to success."""
    results = iter([_result(1, "failed"), _result(0)])
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])
    monkeypatch.setattr(
        fuzz, "run_pytest", lambda *args, **kwargs: next(results)
    )
    output_path = tmp_path / "sticky-failure"

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--batches",
            "2",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code == 1
    assert metadata["status"] == "failed"
    assert [batch["status"] for batch in metadata["batches"]] == [
        "failed",
        "passed",
    ]


def test_hard_timeout_is_shared_across_batches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Repeated batches share one runner deadline."""
    observed_timeouts = []
    monotonic_values = iter([0.0, 100.0, 850.0])
    monkeypatch.setattr(
        "scripts.fuzz.time.monotonic", lambda: next(monotonic_values)
    )
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])

    def run_batch(
        command: List[str],
        environment: object,
        timeout_seconds: int,
        output_dir: Path,
    ) -> fuzz.BatchResult:
        observed_timeouts.append(timeout_seconds)
        return _result(0)

    monkeypatch.setattr(fuzz, "run_pytest", run_batch)

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--profile",
            "local",
            "--batches",
            "2",
            "--output-dir",
            str(tmp_path / "shared-deadline"),
        ]
    )

    assert return_code == 0
    assert observed_timeouts == [800, 50]


def test_default_run_repeats_completed_batches_until_generation_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The generation deadline is checked only between default batches."""
    observed_batches = []
    monotonic_values = iter([0.0, 0.0, 59.0, 59.0, 61.0])
    monkeypatch.setattr(
        "scripts.fuzz.time.monotonic", lambda: next(monotonic_values)
    )
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])

    def run_batch(
        command: List[str],
        environment: object,
        timeout_seconds: int,
        output_dir: Path,
    ) -> fuzz.BatchResult:
        assert isinstance(environment, dict)
        observed_batches.append(environment["ZENML_FUZZ_BATCH"])
        return _result(0)

    monkeypatch.setattr(fuzz, "run_pytest", run_batch)

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--profile",
            "local",
            "--output-dir",
            str(tmp_path / "generation-deadline"),
        ]
    )

    assert return_code == 0
    assert observed_batches == ["1", "2"]


def test_interrupted_run_preserves_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An interrupted runner exits nonzero and preserves its evidence."""
    output_path = tmp_path / "interrupted"
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])
    monkeypatch.setattr(
        fuzz,
        "run_pytest",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code == 130
    assert metadata["status"] == "interrupted"
    assert metadata["source_revision"]


def test_process_start_failure_is_recorded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A process startup failure is an explicit setup failure."""
    output_path = tmp_path / "setup-failed"
    monkeypatch.setattr(fuzz, "missing_dependencies", lambda suite: [])
    monkeypatch.setattr(
        fuzz,
        "run_pytest",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("process unavailable")
        ),
    )

    return_code = fuzz.main(
        [
            "--suite",
            "filters",
            "--output-dir",
            str(output_path),
        ]
    )

    metadata = json.loads((output_path / "run.json").read_text())
    assert return_code != 0
    assert metadata["status"] == "setup_failed"
    assert metadata["setup_error"] == "process unavailable"


class _InterruptedProcess:
    """Process double that is interrupted while waiting."""

    pid = 1000
    returncode = None

    def wait(self, timeout: int) -> int:
        """Simulate an interrupt."""
        raise KeyboardInterrupt


class _TimedOutProcess:
    """Process double that exceeds its hard timeout."""

    pid = 1001
    returncode = None

    def wait(self, timeout: int) -> int:
        """Simulate a hard timeout."""
        raise subprocess.TimeoutExpired("pytest", timeout)


@pytest.mark.parametrize(
    ("process", "exception"),
    [(_InterruptedProcess(), KeyboardInterrupt), (_TimedOutProcess(), None)],
)
def test_interruption_terminates_owned_process(
    process: object,
    exception: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Interrupts and timeouts terminate the owned pytest process group."""
    terminated = []
    monkeypatch.setattr(
        "scripts.fuzz.subprocess.Popen", lambda *args, **kwargs: process
    )

    def terminate(child: object) -> bool:
        terminated.append(child)
        return True

    monkeypatch.setattr(
        fuzz,
        "terminate_process",
        terminate,
    )

    if exception is KeyboardInterrupt:
        with pytest.raises(KeyboardInterrupt):
            fuzz.run_pytest(["pytest"], {}, 1, tmp_path)
    else:
        result = fuzz.run_pytest(["pytest"], {}, 1, tmp_path)
        assert result.status == "timed_out"
        assert result.return_code != 0

    assert terminated == [process]


class _UnkillableProcess:
    """Process double that remains alive after SIGKILL."""

    pid = 1002
    returncode = None

    def __init__(self) -> None:
        self.wait_timeouts: List[int] = []

    def poll(self) -> None:
        """Report that the process is still running."""
        return None

    def wait(self, timeout: int) -> int:
        """Record every bounded wait and continue timing out."""
        self.wait_timeouts.append(timeout)
        raise subprocess.TimeoutExpired("pytest", timeout)


def test_sigkill_wait_is_bounded_and_teardown_failure_is_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A process surviving SIGKILL cannot hang the fuzz runner."""
    process = _UnkillableProcess()
    signals = []
    monkeypatch.setattr(
        "scripts.fuzz.subprocess.Popen", lambda *args, **kwargs: process
    )
    monkeypatch.setattr(
        "scripts.fuzz.os.killpg",
        lambda pid, sent_signal: signals.append((pid, sent_signal)),
    )

    result = fuzz.run_pytest(["pytest"], {}, 1, tmp_path)

    assert result.status == "teardown_failed"
    assert result.return_code != 0
    assert process.wait_timeouts == [
        1,
        fuzz.PROCESS_TERMINATION_TIMEOUT_SECONDS,
        fuzz.PROCESS_TERMINATION_TIMEOUT_SECONDS,
    ]
    assert signals == [
        (process.pid, signal.SIGTERM),
        (process.pid, signal.SIGKILL),
    ]


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX process groups only"
)
def test_timeout_unwinds_pytest_cleanup(tmp_path: Path) -> None:
    """SIGTERM lets the fuzz child finish cleanup before it exits."""
    marker = tmp_path / "cleanup-marker"
    environment = os.environ.copy()
    environment.update(
        {
            "ZENML_FUZZ": "1",
            "ZENML_FUZZ_TIMEOUT_CLEANUP_MARKER": str(marker),
        }
    )
    result = fuzz.run_pytest(
        [
            sys.executable,
            "-m",
            "pytest",
            str(fuzz.FUZZ_ROOT / "timeout_cleanup_probe.py"),
            "--confcutdir",
            str(fuzz.FUZZ_ROOT),
            "-q",
            *(
                item
                for plugin in fuzz.PYTEST_PLUGIN_BLOCKLIST
                for item in ("-p", plugin)
            ),
        ],
        environment,
        timeout_seconds=1,
        output_dir=tmp_path,
    )

    assert result.status == "timed_out"
    assert marker.read_text() == "cleaned\n"
