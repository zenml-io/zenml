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
from typing import Generator

import pytest

from zenml.client import Client
from zenml.constants import ENV_ZENML_ACTIVE_PROJECT_ID
from zenml.utils.string_utils import random_str


def _is_medium_tier() -> bool:
    """Return whether tests are running in the medium CI tier."""
    return os.environ.get("ZENML_CI_TIER") == "medium"


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
    """Skip global-state tests in medium-tier CI."""
    if not _is_medium_tier():
        return

    for item in items:
        if item.get_closest_marker("global_state"):
            item.add_marker(
                pytest.mark.skip(
                    reason="global-state test runs outside medium tier"
                )
            )
