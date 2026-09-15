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
"""Tests that ordinary pytest collection excludes generated fuzz tests."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_ordinary_collection_does_not_import_fuzz_modules(
    tmp_path: Path,
) -> None:
    """Root collection ignores the fuzz directory without optional tools."""
    repository_root = Path(__file__).parents[2]
    test_root = tmp_path / "tests"
    fuzz_root = test_root / "fuzz"
    fuzz_root.mkdir(parents=True)
    shutil.copy(repository_root / "tests" / "conftest.py", test_root)
    sentinel = tmp_path / "fuzz-imported"
    (test_root / "test_regular.py").write_text("def test_regular(): pass\n")
    (fuzz_root / "test_sentinel.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('imported')\n"
        "def test_fuzz(): pass\n"
    )
    environment = os.environ.copy()
    environment.pop("ZENML_FUZZ", None)
    environment["PYTHONPATH"] = str(repository_root)

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
