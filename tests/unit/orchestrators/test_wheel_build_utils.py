#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for wheel build utilities."""

import os
from types import SimpleNamespace
from typing import Any

from zenml.orchestrators import wheel_build_utils


def test_sanitize_name_uses_ascii_package_characters() -> None:
    """Tests package names use explicit ASCII-only sanitization."""
    assert (
        wheel_build_utils.sanitize_name("My Project_Δ/2026!")
        == "my-project---2026"
    )


def test_create_wheel_uses_subprocess_cwd_without_mutating_global_cwd(
    mocker: Any,
    tmp_path: Any,
) -> None:
    """Tests wheel creation uses subprocess cwd instead of os.chdir."""
    wheel_path = tmp_path / "project-0.1.0-py3-none-any.whl"
    wheel_path.write_bytes(b"wheel")
    original_cwd = os.getcwd()

    run_mock = mocker.patch.object(
        wheel_build_utils.subprocess,
        "run",
        return_value=SimpleNamespace(stdout=b"", stderr=b""),
    )
    mocker.patch.object(
        wheel_build_utils.zipfile, "is_zipfile", return_value=True
    )

    created_wheel_path = wheel_build_utils.create_wheel(str(tmp_path))

    assert os.getcwd() == original_cwd
    assert created_wheel_path == str(wheel_path)
    run_mock.assert_called_once_with(
        [wheel_build_utils.sys.executable, "-m", "pip", "wheel", "."],
        check=True,
        capture_output=True,
        cwd=str(tmp_path),
    )
