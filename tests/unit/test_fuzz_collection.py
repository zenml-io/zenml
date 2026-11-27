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
"""Unit tests for opt-in fuzzing isolation, runner, and CI invariants."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from scripts import fuzz

REPOSITORY_ROOT = Path(__file__).parents[2]
_SHA_PIN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")


def test_ordinary_collection_does_not_import_fuzz_modules(
    tmp_path: Path,
) -> None:
    """Root collection ignores the fuzz directory without optional tools."""
    test_root = tmp_path / "tests"
    fuzz_root = test_root / "fuzz"
    fuzz_root.mkdir(parents=True)
    shutil.copy(REPOSITORY_ROOT / "tests" / "conftest.py", test_root)
    sentinel = tmp_path / "fuzz-imported"
    (test_root / "test_regular.py").write_text("def test_regular(): pass\n")
    (fuzz_root / "test_sentinel.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('imported')\n"
        "def test_fuzz(): pass\n"
    )
    environment = os.environ.copy()
    environment.pop("ZENML_FUZZ", None)
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            str(test_root),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "test_regular.py::test_regular" in result.stdout
    assert "test_sentinel" not in result.stdout
    assert not sentinel.exists()


def test_fuzz_conftest_overrides_hypothesis_ci_profile_on_gha(
    tmp_path: Path,
) -> None:
    """Hosted CI runs stay randomized and keep a directory-backed corpus."""
    corpus_dir = tmp_path / "corpus"
    probe = tmp_path / "test_profile_probe.py"
    shutil.copy(REPOSITORY_ROOT / "tests" / "fuzz" / "conftest.py", tmp_path)
    probe.write_text(
        "from pathlib import Path\n"
        "from hypothesis import settings\n"
        "from hypothesis.database import DirectoryBasedExampleDatabase\n\n"
        "def test_profile_is_randomized_with_database():\n"
        "    active = settings()\n"
        "    assert active.max_examples == 500\n"
        "    assert active.deadline is None\n"
        "    assert active.derandomize is False\n"
        "    assert isinstance(active.database, DirectoryBasedExampleDatabase)\n"
        f"    assert Path(active.database.path) == Path({str(corpus_dir / 'examples')!r})\n"
    )
    environment = os.environ.copy()
    environment.update(
        {
            "CI": "true",
            "GITHUB_ACTIONS": "true",
            "HYPOTHESIS_STORAGE_DIRECTORY": str(corpus_dir),
            "ZENML_FUZZ": "1",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(probe),
            "--confcutdir",
            str(tmp_path),
            "--hypothesis-profile=nightly",
            "-q",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_runner_command_is_isolated_and_excludes_self_tests(
    tmp_path: Path,
) -> None:
    """The runner targets only the selected fuzz file with clean flags."""
    config = fuzz.parse_args(
        [
            "--suite",
            "filters",
            "--backend",
            "sqlite",
            "--profile",
            "pr",
            "--seed",
            "42",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    command = fuzz.build_pytest_command(config)

    assert command[3] == str(fuzz.FUZZ_ROOT / "test_filters.py")
    assert [arg for arg in command if arg.endswith(".py")] == [
        str(fuzz.FUZZ_ROOT / "test_filters.py")
    ]
    assert "--confcutdir" in command
    assert "--durations=20" in command
    assert "--hypothesis-show-statistics" in command
    assert "--hypothesis-profile=pr" in command
    assert "--hypothesis-seed=42" in command
    assert "no:rerunfailures" in command
    assert "no:randomly" in command


@pytest.mark.parametrize(
    "arguments",
    [
        ["--suite", "cli", "--backend", "sqlite"],
        ["--suite", "filters", "--backend", "none"],
        [
            "--suite",
            "filters",
            "--reproduce",
            "tests/fuzz/test_cli.py::test_other",
        ],
    ],
)
def test_runner_rejects_invalid_selections(
    arguments: list[str], tmp_path: Path
) -> None:
    """Invalid suite/backend/reproduce choices fail before creating files."""
    output_dir = tmp_path / "should-not-exist"
    with pytest.raises(SystemExit):
        fuzz.parse_args([*arguments, "--output-dir", str(output_dir)])
    assert not output_dir.exists()


@pytest.mark.parametrize("workflow_name", ["fuzz-pr.yml", "fuzz-nightly.yml"])
def test_fuzz_workflows_preserve_security_invariants(
    workflow_name: str,
) -> None:
    """Check security invariants without pinning literal Action SHAs."""
    path = REPOSITORY_ROOT / ".github" / "workflows" / workflow_name
    loaded: Dict[str, Any] = yaml.load(  # nosec B506
        path.read_text(), Loader=yaml.BaseLoader
    )

    assert "pull_request_target" not in loaded["on"]
    for job_name, job in loaded["jobs"].items():
        if job_name != "report":
            perms = job.get("permissions", loaded.get("permissions", {}))
            assert perms == {"contents": "read"}
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses is not None:
                assert _SHA_PIN.match(uses), f"Action not SHA-pinned: {uses}"
                if uses.startswith("actions/checkout@"):
                    assert step["with"]["persist-credentials"] == "false"
