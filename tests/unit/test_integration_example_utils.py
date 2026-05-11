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

"""Tests for integration example utilities."""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.integration.examples.utils import IntegrationTestExample
from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT


def test_integration_examples_do_not_inherit_databricks_source_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test example subprocesses ignore stale Databricks wheel state."""
    (tmp_path / "run.py").write_text("")
    monkeypatch.setenv(
        ENV_ZENML_CUSTOM_SOURCE_ROOT, "/tmp/stale-databricks-root"
    )
    monkeypatch.setenv(
        "ZENML_DATABRICKS_WHEEL_PACKAGE", "stale_databricks_package"
    )
    captured_env: dict[str, str] = {}

    def fake_run(
        *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        del args
        captured_env.update(kwargs["env"])
        return subprocess.CompletedProcess(
            args=kwargs["args"] if "args" in kwargs else [],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    IntegrationTestExample(name="example", path=tmp_path)()

    assert ENV_ZENML_CUSTOM_SOURCE_ROOT not in captured_env
    assert "ZENML_DATABRICKS_WHEEL_PACKAGE" not in captured_env
