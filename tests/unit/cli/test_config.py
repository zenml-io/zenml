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
"""Tests for the analytics CLI commands."""

from importlib import import_module
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest
from click.testing import CliRunner

from zenml.analytics.enums import AnalyticsEvent

config_module = import_module("zenml.cli.config")


@pytest.mark.parametrize(
    "args, expected",
    [
        (["--scope", "project"], {"install_scope": "project"}),
        ([], {}),
    ],
)
def test_report_install_tracks_one_script_install_event(
    monkeypatch: pytest.MonkeyPatch, args: List[str], expected: Dict[str, str]
) -> None:
    """The install script's report sends one event naming the install method."""
    tracked: List[Tuple[Any, Dict[str, Any]]] = []
    monkeypatch.setattr(
        config_module,
        "GlobalConfiguration",
        lambda: SimpleNamespace(zen_store=None),
    )
    monkeypatch.setattr(
        config_module,
        "track",
        lambda event, metadata: tracked.append((event, metadata)),
    )

    result = CliRunner().invoke(
        config_module.analytics, ["report-install", *args]
    )

    assert result.exit_code == 0, result.output
    assert tracked == [
        (
            AnalyticsEvent.INSTALL_SCRIPT_COMPLETED,
            {"install_method": "script", **expected},
        )
    ]
    assert config_module.report_install.hidden
