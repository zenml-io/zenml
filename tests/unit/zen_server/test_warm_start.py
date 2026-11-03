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
"""Tests for the warm start of a ZenML Pro server."""

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import requests
from pydantic import ValidationError

from zenml.zen_server import warm_start
from zenml.zen_server.warm_start import WorkspaceIdentity


def test_loading_server_code_reads_no_settings() -> None:
    """A new read of the settings while loading would keep the wrong values."""
    code = (
        "import sys\n"
        "from zenml.zen_server.warm_start import API_MODULE, load_server_code\n"
        "from zenml.zen_server import utils\n"
        "load_server_code()\n"
        "assert utils._server_config is None\n"
        "assert API_MODULE not in sys.modules\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_identity_refuses_a_claim_without_an_organization() -> None:
    """A server must never finish starting without a customer."""
    with pytest.raises(ValidationError):
        WorkspaceIdentity.model_validate({"claimed": True})


def test_identity_ignores_variables_it_does_not_expect() -> None:
    """Values from the API become environment variables, so only allow some."""
    identity = WorkspaceIdentity.model_validate(
        {
            "claimed": True,
            "organization_id": str(uuid4()),
            "environment": {"LD_PRELOAD": "/tmp/library.so"},
        }
    )
    assert identity.environment == {}


def test_ready_report_survives_a_long_api_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only this report opens the workspace, so an outage must not end it."""
    outage_seconds = 3600
    now = [0.0]
    sleeps = []
    reported_at = []

    def sleep(seconds: float) -> None:
        now[0] += seconds
        sleeps.append(seconds)

    def report_ready() -> None:
        if now[0] < 5:
            raise KeyError("access_token")
        if now[0] < outage_seconds:
            raise requests.ConnectionError("API is down")
        reported_at.append(now[0])

    monkeypatch.setattr(
        warm_start,
        "time",
        SimpleNamespace(time=lambda: now[0], sleep=sleep),
    )
    monkeypatch.setattr("urllib.request.urlopen", MagicMock())
    monkeypatch.setattr(
        warm_start,
        "_ProApi",
        lambda: SimpleNamespace(report_ready=report_ready),
    )

    warm_start._report_when_serving(port=1)

    assert len(reported_at) == 1
    assert sleeps[0] == warm_start.ASK_INTERVAL_SECONDS
    assert max(sleeps) == warm_start.READY_REPORT_MAX_INTERVAL_SECONDS
