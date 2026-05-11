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

"""Tests for Databricks Python wheel task entrypoint resolution."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_databricks_python_wheel_task_resolves_zenml_entrypoint() -> None:
    """Tests package-root entrypoint resolution used by Databricks."""
    command = textwrap.dedent(
        """
        import importlib

        package_name = "zenml"
        entry_point = "entrypoint.main"

        target = importlib.import_module(package_name)
        for attribute in entry_point.split("."):
            target = getattr(target, attribute)

        assert callable(target)
        """
    )
    env = os.environ.copy()
    env.setdefault("ZENML_ANALYTICS_OPT_IN", "false")
    env.setdefault("ZENML_ENABLE_RICH_TRACEBACK", "false")

    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "Databricks-style ZenML wheel entrypoint resolution failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
