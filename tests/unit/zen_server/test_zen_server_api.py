#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for the ZenML server API."""

from pathlib import Path

import anyio
import pytest
from fastapi import HTTPException, Request
from pytest_mock import MockerFixture

from zenml.zen_server import zen_server_api


def test_dashboard_route_without_dashboard_assets_returns_404(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test that SPA routes return 404 when dashboard assets are missing."""
    mocker.patch.object(
        zen_server_api, "dashboard_directory", return_value=str(tmp_path)
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/devices/verify",
            "headers": [],
        }
    )

    with pytest.raises(HTTPException, match="Dashboard assets") as exc_info:
        anyio.run(zen_server_api.catch_all, request, "devices/verify")

    assert exc_info.value.status_code == 404
