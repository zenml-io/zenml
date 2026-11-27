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
"""`zenml_mcp` loads no ZenML core module.

A server that hosts the MCP tools installs `zenml` with other versions of
pydantic and OpenTelemetry than ZenML pins, so ZenML core must never run
there: importing anything under `zenml.` would run `zenml/__init__.py`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

import zenml_mcp  # noqa: E402

_IMPORT_EVERYTHING = """
import json, pkgutil, sys
import zenml_mcp
names = [m.name for m in pkgutil.walk_packages(zenml_mcp.__path__, "zenml_mcp.")]
for name in names:
    __import__(name)
from zenml_mcp.tools import TOOL_SPECS
for spec in TOOL_SPECS:
    spec.arguments
print(json.dumps({
    "file": zenml_mcp.__file__,
    "imported": names,
    "tools": len(TOOL_SPECS),
    "core": sorted(m for m in sys.modules if m == "zenml" or m.startswith("zenml.")),
}))
"""


def test_importing_every_module_loads_no_zenml_core_module() -> None:
    """Every `zenml_mcp` module, and every tool's argument model."""
    package = Path(zenml_mcp.__file__).parent
    # The package under test, not an installed copy: its parent goes first
    # on the path of a fresh interpreter.
    found = subprocess.run(
        [sys.executable, "-c", _IMPORT_EVERYTHING],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(package.parent)},
    )
    report = json.loads(found.stdout)
    assert Path(report["file"]).parent == package
    assert "zenml_mcp.server" in report["imported"]
    assert report["tools"] > 0
    assert report["core"] == []
