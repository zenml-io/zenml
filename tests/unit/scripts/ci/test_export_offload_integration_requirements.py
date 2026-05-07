"""Tests for offload integration requirement export."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch
from scripts.ci.export_offload_integration_requirements import (
    export_requirements,
)


class _FakeRegistry:
    integrations = {"aws": object, "tensorflow": object}

    def select_integration_requirements(
        self, integration_name: str
    ) -> list[str]:
        return [f"{integration_name}-requirement"]


def test_export_requirements_uses_registry_and_ignores_blocked_integrations(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Generated requirements come from ZenML metadata, not a fixed file."""
    registry_module = ModuleType("zenml.integrations.registry")
    registry_module.integration_registry = _FakeRegistry()
    monkeypatch.setitem(sys.modules, "zenml", ModuleType("zenml"))
    monkeypatch.setitem(
        sys.modules, "zenml.integrations", ModuleType("zenml.integrations")
    )
    monkeypatch.setitem(
        sys.modules, "zenml.integrations.registry", registry_module
    )

    output_file = tmp_path / "integration-requirements.txt"
    export_requirements(output_file)

    requirements = output_file.read_text()
    assert "aws-requirement" in requirements
    assert "tensorflow-requirement" not in requirements
    assert "pyyaml>=6.0.1" in requirements
