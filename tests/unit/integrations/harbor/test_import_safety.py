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
"""Import-safety tests: core zenml must not require Harbor."""

import subprocess
import sys

import pytest

from zenml.integrations.harbor import HarborIntegration


def test_harbor_free_modules_do_not_import_harbor() -> None:
    """The registry-facing modules must be importable without Harbor."""
    code = (
        "import sys\n"
        "import zenml.integrations.harbor\n"
        "import zenml.integrations.harbor.models\n"
        "import zenml.integrations.harbor.utils\n"
        "import zenml.integrations.harbor.materializers\n"
        "assert 'harbor' not in sys.modules, "
        "'harbor was imported by a registry-facing module'\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_harbor_integration_is_registered() -> None:
    """The integration registers itself via the filesystem walk."""
    from zenml.integrations.registry import integration_registry

    assert "harbor" in integration_registry.integrations


def test_requirements_are_gated_on_python_version() -> None:
    """Below Harbor's minimum Python, no requirements are reported."""
    assert HarborIntegration.get_requirements(python_version="3.10") == []
    assert HarborIntegration.get_requirements(python_version="3.11") == []
    assert HarborIntegration.get_requirements(python_version="3.12") == [
        "harbor>=0.8,<0.9"
    ]
    assert HarborIntegration.get_requirements(python_version="3.13") == [
        "harbor>=0.8,<0.9"
    ]
    # Single-component version strings fall back to minor 0.
    assert HarborIntegration.get_requirements(python_version="3") == []


def test_requirements_fall_back_to_running_interpreter() -> None:
    """Without an explicit version, the running interpreter decides."""
    expected = ["harbor>=0.8,<0.9"] if sys.version_info[:2] >= (3, 12) else []
    assert HarborIntegration.get_requirements() == expected


def test_interpreter_gate_logs_debug_not_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The interpreter-fallback path must never warn.

    `check_installation` hits it on every pipeline run for every user,
    Harbor-related or not.
    """
    import logging
    from unittest.mock import patch

    with patch.object(sys, "version_info", (3, 10, 0)):
        with caplog.at_level(logging.WARNING):
            assert HarborIntegration.get_requirements() == []
            assert HarborIntegration.check_installation() is False
    assert "Harbor integration requires" not in caplog.text
