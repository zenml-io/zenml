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

"""Integration-test CI policy hooks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator

import pytest

from zenml.client import Client
from zenml.constants import ENV_ZENML_ACTIVE_PROJECT_ID
from zenml.utils.string_utils import random_str


def _is_medium_tier() -> bool:
    """Return whether tests are running in the medium CI tier."""
    return os.environ.get("ZENML_CI_TIER") == "medium"


def _load_quarantined_tests() -> dict[str, str]:
    """Load tests quarantined for the current CI tier."""
    registry_path = Path(__file__).parents[2] / ".github/quarantined-tests.yml"
    if not registry_path.exists():
        return {}

    import yaml

    data: dict[str, Any] = (
        yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    )
    quarantined: dict[str, str] = {}
    for entry in data.get("quarantined", []):
        if "medium" not in entry.get("skip_in", []):
            continue
        quarantined[str(entry["test_id"])] = str(
            entry.get("reason", "quarantined")
        )
    return quarantined


def pytest_configure(config: pytest.Config) -> None:
    """Register CI markers."""
    config.addinivalue_line(
        "markers",
        "global_state: integration test intentionally mutates server-global state",
    )


@pytest.fixture
def zenml_workspace(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create an isolated ZenML project for a workspace-safe test."""
    client = Client()
    original_project_id = client.active_project.id
    project_name = f"pytest_{random_str(8).lower()}"
    project = client.create_project(
        name=project_name,
        description=f"Isolated project for {request.node.nodeid}",
    )

    client.set_active_project(project.id)
    monkeypatch.setenv(ENV_ZENML_ACTIVE_PROJECT_ID, str(project.id))

    try:
        yield project_name
    finally:
        monkeypatch.setenv(
            ENV_ZENML_ACTIVE_PROJECT_ID, str(original_project_id)
        )
        client.set_active_project(original_project_id)
        client.delete_project(project_name)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip medium-tier tests with active quarantines."""
    if not _is_medium_tier():
        return

    quarantined = _load_quarantined_tests()
    for item in items:
        if item.get_closest_marker("global_state"):
            item.add_marker(
                pytest.mark.skip(
                    reason="global-state test runs outside medium tier"
                )
            )
            continue

        reason = quarantined.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.skip(reason=f"quarantined: {reason}"))
